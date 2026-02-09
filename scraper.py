import asyncio
import csv
import os
import re
import json
import argparse
import sys
from datetime import datetime
import pandas as pd
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

class MetaJobScraper:
    def __init__(self, base_url="https://www.metacareers.com", concurrency=5):
        self.base_url = base_url
        self.search_url = f"{base_url}/jobsearch"
        self.jobs = []
        self.concurrency = concurrency
        self.semaphore = asyncio.Semaphore(concurrency)

    async def run(self, max_pages=None):
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
            
            # Step 1: Collect all job links
            job_links = await self.get_all_job_links(context, max_pages)
            print(f"Total jobs to scrape: {len(job_links)}")
            
            # Step 2: Scrape job details in parallel
            tasks = []
            for link in job_links:
                tasks.append(self.scrape_job_with_semaphore(context, link))
            
            # Execute tasks
            results = await asyncio.gather(*tasks)
            self.jobs = [r for r in results if r]
            
            # Generate timestamped filename: meta_jobs_HHMM_dd-MMM-YYYY
            timestamp = datetime.now().strftime("%H%M_%d-%b-%Y")
            base_filename = f"meta_jobs_{timestamp}"
            
            # Final Save in multiple formats
            self.save_to_formats(base_filename)
            
            await browser.close()
            print(f"Scraping complete. Found {len(self.jobs)} jobs.")

    async def get_all_job_links(self, context, max_pages):
        page = await context.new_page()
        print(f"Opening first page to determine total pages...")
        await page.goto(self.search_url)
        await page.wait_for_timeout(5000)
        
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await page.wait_for_timeout(2000)
        
        total_pages_info = await page.evaluate(r"""() => {
            const match = document.body.innerText.match(/Page \d+ of (\d+)/);
            return match ? parseInt(match[1]) : 1;
        }""")
        print(f"Total pages available: {total_pages_info}")
        
        limit_pages = min(total_pages_info, max_pages) if max_pages else total_pages_info
        print(f"Scraping links from first {limit_pages} pages...")
        
        
        async def scrape_index_page(page_num):
            async with self.semaphore:
                p = await context.new_page()
                url = f"{self.search_url}?page={page_num}"
                try:
                    await p.goto(url)
                    await p.wait_for_timeout(3000)
                    page_links = await p.evaluate("""() => {
                        return Array.from(document.querySelectorAll('a[href*="/profile/job_details/"]'))
                                    .map(a => a.href);
                    }""")
                    await p.close()
                    return page_links
                except Exception as e:
                    print(f"Error scraping index page {page_num}: {e}")
                    await p.close()
                    return []

        index_tasks = [scrape_index_page(i) for i in range(1, limit_pages + 1)]
        results = await asyncio.gather(*index_tasks)
        
        ordered_links = []
        seen = set()
        for r in results:
            if r:
                for link in r:
                    if link not in seen:
                        ordered_links.append(link)
                        seen.add(link)
        
        await page.close()
        return ordered_links

    async def scrape_job_with_semaphore(self, context, url):
        async with self.semaphore:
            page = await context.new_page()
            result = await self.scrape_job_details(page, url)
            await page.close()
            return result

    def clean_html_field(self, field_val):
        if not field_val: return ""
        if isinstance(field_val, str) and field_val.strip().startswith('{'):
            try:
                field_val = json.loads(field_val)
            except: pass
        if isinstance(field_val, dict) and '__html' in field_val:
            field_val = field_val['__html']
        if not isinstance(field_val, str): return str(field_val)
        
        # Replace common tags with newlines or spaces to preserve lists
        content = field_val.replace('</li>', '\n• ').replace('<ul>', '\n').replace('</ul>', '\n')
        content = content.replace('<br>', '\n').replace('<br/>', '\n').replace('</p>', '\n\n')
        
        # Remove remaining tags
        clean_text = re.sub('<[^<]+?>', '', content)
        
        # Clean entities
        clean_text = clean_text.replace('&quot;', '"').replace('&#039;', "'").replace('&amp;', '&')
        clean_text = clean_text.replace('&nbsp;', ' ').replace('&bull;', '•')
        
        return clean_text.strip()

    def extract_links_from_field(self, field_val):
        if not field_val: return []
        if isinstance(field_val, str) and field_val.strip().startswith('{'):
            try:
                field_val = json.loads(field_val)
            except: pass
        if isinstance(field_val, dict) and '__html' in field_val:
            field_val = field_val['__html']
        if not isinstance(field_val, str): return []
        
        soup = BeautifulSoup(field_val, 'html.parser')
        links = []
        for a in soup.find_all('a', href=True):
            href = a['href']
            if href.startswith('/'):
                href = self.base_url + href
            if href not in links:
                links.append(href)
        return links

    async def scrape_job_details(self, page, url):
        try:
            await page.goto(url)
            await page.wait_for_timeout(5000)

            json_data = await page.evaluate("""() => {
                const scripts = Array.from(document.querySelectorAll('script[type="application/json"]'));
                for (const script of scripts) {
                    const content = script.textContent;
                    if (content.includes('xcp_requisition_job_description')) {
                        try {
                            const parsed = JSON.parse(content);
                            let jobData = null;
                            const findKey = (obj, key) => {
                                if (obj && typeof obj === 'object') {
                                    if (obj[key]) return obj[key];
                                    for (const k in obj) {
                                        const res = findKey(obj[k], key);
                                        if (res) return res;
                                    }
                                }
                                return null;
                            };
                            jobData = findKey(parsed, 'xcp_requisition_job_description');
                            if (jobData) return jobData;
                        } catch (e) {}
                    }
                }
                return null;
            }""")

            if json_data:
                res = {}
                res['job_link'] = url
                res['job_name'] = json_data.get('title', '')
                
                # 1. Departments improvement - include internal and external
                depts = json_data.get('internal_departments', []) + json_data.get('departments', [])
                # De-duplicate while preserving order
                seen = set()
                final_depts = []
                for d in depts:
                    if d not in seen:
                        final_depts.append(d)
                        seen.add(d)
                res['job_department'] = ", ".join(final_depts)
                
                res['job_location'] = ", ".join(json_data.get('locations', []))
                
                # 2. Split Qualifications
                min_quals = []
                for item in json_data.get('minimum_qualifications', []):
                    min_quals.append(f"• {item.get('item', '')}")
                res['minimum_qualifications'] = "\n".join(min_quals)
                
                pref_quals = []
                for item in json_data.get('preferred_qualifications', []):
                    pref_quals.append(f"• {item.get('item', '')}")
                res['preferred_qualifications'] = "\n".join(pref_quals)

                # Legacy field for compatibility
                res['job_qualification'] = f"Minimum:\n{res['minimum_qualifications']}\n\nPreferred:\n{res['preferred_qualifications']}"

                # Descriptions
                res['job_description'] = self.clean_html_field(json_data.get('description', ''))
                
                res_list = []
                for item in json_data.get('responsibilities', []):
                    res_list.append(f"• {item.get('item', '')}")
                res['job_responsibilities'] = "\n".join(res_list)
                
                res['about_meta'] = self.clean_html_field(json_data.get('boiler_plate_intro', ''))
                
                # 3. & 4. Salary and Compensation
                comp_list = json_data.get('public_compensation', [])
                if comp_list:
                    c = comp_list[0]
                    sal_str = f"{c.get('compensation_amount_minimum', '')} to {c.get('compensation_amount_maximum', '')}"
                    if c.get('has_bonus'): sal_str += " + bonus"
                    if c.get('has_equity'): sal_str += " + equity"
                    sal_str += " + benefits" # Standard suffix as requested
                    res['salary'] = sal_str
                    
                    # Try JSON field first
                    extra_info = self.clean_html_field(c.get('error_apology_note', ''))
                    
                    # Fallback to DOM if JSON field is empty
                    if not extra_info:
                        extra_info = await page.evaluate("""() => {
                            const salarySpan = Array.from(document.querySelectorAll('span'))
                                .find(s => s.innerText.includes('/year') || s.innerText.includes('/month') || s.innerText.includes('/hour') || s.innerText.includes('/week'));
                            if (!salarySpan) return "";
                            // Find the container that holds the salary and the text below it
                            let parent = salarySpan.parentElement;
                            while (parent && parent.innerText.length < 100) {
                                parent = parent.parentElement;
                            }
                            if (!parent) return "";
                            
                            // Extract text below the salary span
                            // Often it's in a sibling div or the same parent
                            const paragraphs = Array.from(parent.querySelectorAll('span, div'));
                            const salaryIdx = paragraphs.findIndex(p => p === salarySpan || p.contains(salarySpan));
                            
                            // Let's just collect all text in that section that isn't the salary itself
                            const policyText = paragraphs
                                .slice(salaryIdx + 1)
                                .map(p => p.innerText)
                                .find(t => t && t.includes('Individual compensation is determined'));
                                
                            return policyText || "";
                        }""")
                    
                    res['compensation_details'] = extra_info
                else:
                    res['salary'] = ""
                    res['compensation_details'] = ""

                # 5. EEO - combine both messages
                eeo_msg = json_data.get('equal_opportunity_message', '')
                acc_msg = json_data.get('accommodations_message', '')
                res['eeo'] = self.clean_html_field(eeo_msg) + "\n\n" + self.clean_html_field(acc_msg)
                
                # 6. Additional Links from all sections
                all_links = set()
                sections_with_html = [
                    json_data.get('boiler_plate_intro', ''),
                    json_data.get('equal_opportunity_message', ''),
                    json_data.get('accommodations_message', ''),
                    json_data.get('description', '')
                ]
                if comp_list:
                    sections_with_html.append(comp_list[0].get('error_apology_note', ''))
                
                for section in sections_with_html:
                    all_links.update(self.extract_links_from_field(section))
                
                # Also fallback DOM links for About Meta and Compensation
                dom_links = await page.evaluate("""() => {
                    const links = [];
                    // About Meta links
                    const aboutH2 = Array.from(document.querySelectorAll('h2')).find(h => h.innerText.includes('About Meta'));
                    if (aboutH2) {
                        let sib = aboutH2.nextElementSibling;
                        while (sib && sib.tagName !== 'HR') {
                            const anchors = sib.querySelectorAll('a');
                            anchors.forEach(a => { if (a.href) links.push(a.href); });
                            sib = sib.nextElementSibling;
                        }
                    }
                    
                    // Compensation/Benefits links
                    const salarySpan = Array.from(document.querySelectorAll('span')).find(s => s.innerText.includes('/year'));
                    if (salarySpan) {
                        let parent = salarySpan.parentElement;
                        while (parent && parent.innerText.length < 100) {
                            parent = parent.parentElement;
                        }
                        if (parent) {
                            const anchors = parent.querySelectorAll('a');
                            anchors.forEach(a => { if (a.href) links.push(a.href); });
                        }
                    }
                    return links;
                }""")
                all_links.update(dom_links)
                
                res['additional_links'] = ", ".join(sorted(list(all_links)))
                
                return res

            return await self.scrape_dom_details(page, url)

        except Exception as e:
            print(f"Error scraping {url}: {e}")
            return None

    async def scrape_dom_details(self, page, url):
        # Improved DOM fallback if JSON fails
        # This handles the requirement to click '+' symbols
        try:
            # Look for expandable locations/departments and click them
            await page.evaluate("""() => {
                const buttons = Array.from(document.querySelectorAll('div, span, button'))
                    .filter(el => {
                        const text = el.innerText || "";
                        return text.includes('+') && (text.includes('Location') || text.includes('more'));
                    });
                buttons.forEach(btn => btn.click());
            }""")
            await page.wait_for_timeout(1000)

            return await page.evaluate("""() => {
                const res = { job_link: window.location.href };
                
                // 1. Job Name - H1 tag below the breadcrumb
                // Usually breadcrumbs are in a nav or have a specific class
                const h1 = document.querySelector('h1');
                res.job_name = h1 ? h1.innerText.trim() : "";

                // 2. Job Location - Expandable section below title
                // We've already clicked, now find the text
                const locationSection = Array.from(document.querySelectorAll('div'))
                    .find(div => div.innerText.includes('Location') && div.querySelector('span'));
                res.job_location = locationSection ? locationSection.innerText.replace(/Location[s]?/, '').trim() : "";

                // 3. Job Department
                const deptSection = Array.from(document.querySelectorAll('div'))
                    .find(div => div.innerText.includes('Department') && div.querySelector('span'));
                res.job_department = deptSection ? deptSection.innerText.replace('Department', '').trim() : "";

                // 4. Job Description - paragraph below Apply Now
                const applyBtn = Array.from(document.querySelectorAll('div')).find(d => d.innerText === 'Apply Now');
                if (applyBtn) {
                    let next = applyBtn.nextElementSibling;
                    while (next && next.innerText.length < 20) next = next.nextElementSibling;
                    res.job_description = next ? next.innerText.trim() : "";
                }

                // 6. Qualifications
                const minQualH2 = Array.from(document.querySelectorAll('h2')).find(h => h.innerText.includes('Minimum Qualifications'));
                if (minQualH2) {
                    const ul = minQualH2.nextElementSibling;
                    res.minimum_qualifications = ul ? ul.innerText.trim() : "";
                }
                const prefQualH2 = Array.from(document.querySelectorAll('h2')).find(h => h.innerText.includes('Preferred Qualifications'));
                if (prefQualH2) {
                    const ul = prefQualH2.nextElementSibling;
                    res.preferred_qualifications = ul ? ul.innerText.trim() : "";
                }

                // 7. About Meta
                const aboutH2 = Array.from(document.querySelectorAll('h2')).find(h => h.innerText.includes('About Meta'));
                if (aboutH2) {
                    const p = aboutH2.nextElementSibling;
                    res.about_meta = p ? p.innerText.trim() : "";
                }

                // 8. Salary
                const salarySpan = Array.from(document.querySelectorAll('span'))
                    .find(s => s.innerText.startsWith('$'));
                res.salary = salarySpan ? salarySpan.innerText.trim() : "";

                // 10. EEO
                const eeoH2 = Array.from(document.querySelectorAll('h2')).find(h => h.innerText.includes('Equal Employment Opportunity'));
                if (eeoH2) {
                    let content = "";
                    let next = eeoH2.nextElementSibling;
                    while (next && next.tagName !== 'H2' && next.tagName !== 'HR') {
                        content += next.innerText + "\\n";
                        next = next.nextElementSibling;
                    }
                    res.eeo = content.trim();
                }

                return res; 
            }""")
        except Exception as e:
            print(f"Error in DOM fallback: {e}")
            return { "job_link": url, "job_name": "Error during DOM fallback" }

    def save_to_formats(self, base_filename):
        if not self.jobs:
            return
        
        df = pd.DataFrame(self.jobs)
        
        # Define column order
        cols = ["job_name", "job_location", "job_department", "job_description", 
                "job_responsibilities", "minimum_qualifications", "preferred_qualifications",
                "about_meta", "salary", "compensation_details", "eeo", "additional_links", "job_link"]
        
        # Ensure all columns exist
        for col in cols:
            if col not in df.columns:
                df[col] = ""
        
        df = df[cols]
        
        # Save to XLSX
        df.to_excel(f"{base_filename}.xlsx", index=False)
        print(f"Saved to {base_filename}.xlsx")
        
        # Save to ODS
        df.to_excel(f"{base_filename}.ods", index=False, engine='odf')
        print(f"Saved to {base_filename}.ods")
        
        # Also keep CSV just in case
        df.to_csv(f"{base_filename}.csv", index=False)
        print(f"Saved to {base_filename}.csv")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Meta Job Scraper")
    parser.add_argument("--max_pages_to_scrap", type=int, help="Maximum number of pages to scrape")
    parser.add_argument("--concurrency", type=int, default=5, help="Number of concurrent browser pages (default: 5)")
    
    args = parser.parse_args()
    
    max_pages = args.max_pages_to_scrap
    
    # Validation per requirements
    if max_pages is not None:
        if max_pages <= 0:
            print(f"Error: max_pages_to_scrap must be greater than 0. Received: {max_pages}")
            sys.exit(1)
            
    scraper = MetaJobScraper(concurrency=args.concurrency)
    
    # Run the scraper
    import asyncio
    try:
        asyncio.run(scraper.run(max_pages=max_pages))
    except KeyboardInterrupt:
        print("\nScraping interrupted by user.")
    except Exception as e:
        print(f"An error occurred: {e}")
