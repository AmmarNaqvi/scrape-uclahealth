# -*- coding: utf-8 -*-
import scrapy
from scrapy.utils.response import open_in_browser
import urlparse


class DoctorsSpider(scrapy.Spider):
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
    # params
    name_search_param = 'limit_FullName'
    name_toggle_param = 'fullname_search'
    page_no_param = 'pageno'

    count = None
    current_page = 1

    def parse(self, response):
        formname = 'form_search'
        formdata = {
            self.name_search_param: 'a',
            self.name_toggle_param: 'true',
        }

        yield scrapy.FormRequest.from_response(response,
                                               formname=formname,
                                               formdata=formdata,
                                               callback=self.doctors_list)

    def doctors_list(self, response):

        for url in response.css(self.doctor_url_selector).extract():
            url = urlparse.urljoin(self.site_url, url)
            yield scrapy.Request(url=url, callback=self.parse_doctors)

        if self.count is None:
            def ceil_div(a, b):
                return -(-a // b)

            page_results = response.css(
                self.page_results_selector).extract_first()
            page_results = page_results.split(' ')

            self.count = ceil_div(int(page_results[-1]), 10)

        if self.current_page <= self.count:
            self.current_page += 1
            formname = 'form_search'
            formdata = {
                self.name_search_param: 'a',
                self.name_toggle_param: 'true',
                self.page_no_param: str(self.current_page)
            }
            yield scrapy.FormRequest.from_response(response,
                                                   formname=formname,
                                                   formdata=formdata,
                                                   callback=self.doctors_list)

    def parse_doctors(self, response):
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
