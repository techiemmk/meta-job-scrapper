Spec
1. The scope of this project is to develop a simple python web scrapper to scrap all the jobs from the metacareer.com website
2. The idea is to traverse all the job from the website 'https://www.metacareers.com/jobsearch' and export it into a csv file
3. There is a section in the 'https://www.metacareers.com/jobsearch' with the title 'All Jobs' where all the jobs got listed. 
   - We need to visit each job page, expand the links with + symbol and scrap the details.
   - The + symbol will be followed by a number, a space and the word 'Location' or 'Locations'
   - The + symbol will be followed by a number, a space and the word 'more'
4. Below the listing there is a pagination. We have to open each page and further scrap it.
5. The job page structure, details to be scrapped and more details can be found below.

Job details page 
1. Job name - H1 tag below the breadcrumb
2. Job location - An expandable section below the title with one or more location
3. Job department - An expandable section below the job location section with one or more department
4. Job description - A paragraph of description below the 'Apply Now' button
5. Job responsibilities - A bulleted list of job responsibilities below the job description section
6. Job qualification - A bulleted list of items below the H2 tag with the title 'Minimum Qualifications' and/or 'Preferred Qualifications'
7. About Meta - A paragraph of data below a H2 tag with the title 'About Meta'
8. Salary - A line below the about meta paragraph that starts with $ symbol
9. Compensation details - A paragraph below the salary line
10 . Equal Employment Opportunity - The data below the H2 tag with the title 'Equal Employment Opportunity'
11. Additional Links - All the hyperlinks between the H2 tag with the title 'About Meta' and before the next <hr> tag
12. Job link - URL of the job page

The scrapped details metioned above have to be captured and stored in the CSV as given in the format below.


