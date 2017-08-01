import urlparse
import scrapy
import re

class DoctorsSpider(scrapy.Spider):
    """A scrapy spider that scrapes uclahealth.org for information of doctors."""
    
    name = 'doctors'
    allowed_domains = ['www.uclahealth.org']
    url = 'https://www.uclahealth.org/body.cfm?id=10&amp;action=list&fullname_search=true&amp;sortby=name&amp;pageno=1&amp;view=list'
    site_url = 'https://www.uclahealth.org/'
    start_urls = [url]

    # CSS selectors
    doctor_url_selector = 'div.list_lastname > a::attr(href)'
    doctor_name_selector = '#updateProfile > span::text'
    doctor_detail_selector = '#div_main_0'
    page_results_selector = '.PageResults > strong::text'

    # XPATH selectors
    doctor_tabs_selector = "//li[contains(concat(' ', normalize-space(@class), ' '), ' tab ')]"
    doctor_tab_name_selector = './a/text()'
    doctor_about_tab_text_selector = '//div[@id=$val]/dl/dd/p/text()'
    doctor_other_tabs_text_selector = '//div[@id=$val]/text()'

    form_name = 'form_search'

    # Search form param names
    name_search_param = 'limit_FullName'
    name_toggle_param = 'fullname_search'
    page_no_param = 'pageno'

    # Search form param values
    name_search_value = 'a'
    name_toggle_value = 'true'

    # Pagination variables
    count = 0
    current_page = 1

    def parse(self, response):
        """Performs search by doctor's fullname with the params name_search and name_toggle.
        Passes on the response to doctors_list().
        """
        formname = self.form_name
        formdata = {
            self.name_search_param: self.name_search_value,
            self.name_toggle_param: self.name_toggle_value,
        }

        yield scrapy.FormRequest.from_response(response,
                                               formname=formname,
                                               formdata=formdata,
                                               callback=self.doctors_list)


    def number_of_pages(self, page_results):
        """takes string of form 'Showing A - B of C, and returns ciel value of C / (B - A)."""        
        page_results = re.findall('\d+', page_results)
        return -(-int(page_results[2]) // (int(page_results[1]) - int(page_results[0])))

    def doctors_list(self, response):
        """Makes request with callback 'parse_doctors' for each doctor on the current page.
        Calculates total number of pages on first call.
        Makes form search request with itself as callback for each page.
        """

        for url in response.css(self.doctor_url_selector).extract():
            url = urlparse.urljoin(self.site_url, url)
            yield scrapy.Request(url=url, callback=self.parse_doctors)

        if self.count == 0:
            page_results = response.css(
                self.page_results_selector).extract_first()
            self.count = self.number_of_pages(page_results)

        if self.current_page <= self.count:
            self.current_page += 1
            formname = self.form_name
            formdata = {
                self.name_search_param: self.name_search_value,
                self.name_toggle_param: self.name_toggle_value,
                self.page_no_param: str(self.current_page)
            }
            yield scrapy.FormRequest.from_response(response,
                                                   formname=formname,
                                                   formdata=formdata,
                                                   callback=self.doctors_list)

    def parse_doctors(self, response):
        """Parses doctor details and yields a dictionary."""

        doctor = {}
        name = response.css(self.doctor_name_selector).extract_first()
        doctor[name] = {}
        details = response.css(self.doctor_detail_selector)
        for index, val in enumerate(details.css('dt')):
            dt_selector = 'dt:nth-of-type(' + str(index) + ')::text'
            dd_selector = 'dd:nth-of-type(' + str(index) + ')::text'
            prop = details.css(dt_selector).extract_first()
            prop_value = details.css(dd_selector).extract_first()
            doctor[name][prop] = prop_value

        for index, tab in enumerate(response.xpath(self.doctor_tabs_selector)):
            prop = tab.xpath(self.doctor_tab_name_selector).extract_first()
            if index == 0:
                prop_value = response.xpath(
                    self.doctor_about_tab_text_selector, val='div_main_' + str(index + 1)).extract_first()
            else:
                prop_value = response.xpath(
                    self.doctor_other_tabs_text_selector, val='div_main_' + str(index + 1)).extract()
            doctor[name][prop] = prop_value

        yield doctor
