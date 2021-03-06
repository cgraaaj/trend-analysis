"""
    The MIT License (MIT)

    Copyright (c) 2014 Vivek Jha

    Permission is hereby granted, free of charge, to any person obtaining a copy
    of this software and associated documentation files (the "Software"), to deal
    in the Software without restriction, including without limitation the rights
    to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
    copies of the Software, and to permit persons to whom the Software is
    furnished to do so, subject to the following conditions:

    The above copyright notice and this permission notice shall be included in all
    copies or substantial portions of the Software.

    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
    IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
    FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
    AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
    LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
    OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
    SOFTWARE.

"""
import six
import ast
import re
import json
import zipfile
import io
import pandas as pd
import os
import requests
from dateutil import parser
from nsetools.bases import AbstractBaseExchange
from nsetools.utils import byte_adaptor
from nsetools.utils import js_adaptor

# import paths differ in python 2 and python 3
if six.PY2:
    from urllib2 import build_opener, HTTPCookieProcessor, Request
    from urllib import urlencode
    from cookielib import CookieJar
elif six.PY3:
    from urllib.request import build_opener, HTTPCookieProcessor, Request
    from urllib.parse import urlencode
    from http.cookiejar import CookieJar

from nsetools.utils import byte_adaptor, js_adaptor
from nsetools.datemgr import mkdate


class Nse(AbstractBaseExchange):
    """
    class which implements all the functionality for
    National Stock Exchange
    """

    __CODECACHE__ = None

    def __init__(self):
        self.opener = self.nse_opener()
        self.headers = self.nse_headers()
        # URL list
        self.get_quote_url = "https://www1.nseindia.com/live_market/dynaContent/live_watch/get_quote/GetQuote.jsp?"
        self.stocks_csv_url = "http://www1.nseindia.com/content/equities/EQUITY_L.csv"
        self.top_gainer_url = "http://www1.nseindia.com/live_market/dynaContent/live_analysis/gainers/niftyGainers1.json"
        self.top_loser_url = "http://www1.nseindia.com/live_market/dynaContent/live_analysis/losers/niftyLosers1.json"
        self.top_fno_gainer_url = "https://www1.nseindia.com/live_market/dynaContent/live_analysis/gainers/fnoGainers1.json"
        self.top_fno_loser_url = "https://www1.nseindia.com/live_market/dynaContent/live_analysis/losers/fnoLosers1.json"
        self.advances_declines_url = (
            "http://www1.nseindia.com/common/json/indicesAdvanceDeclines.json"
        )
        self.index_url = "http://www1.nseindia.com/homepage/Indices1.json"
        self.bhavcopy_base_url = "https://www1.nseindia.com/content/historical/EQUITIES/%s/%s/cm%s%s%sbhav.csv.zip"
        self.bhavcopy_base_filename = "cm%s%s%sbhav.csv"
        self.active_equity_monthly_url = "https://www1.nseindia.com/products/dynaContent/equities/equities/json/mostActiveMonthly.json"
        self.year_high_url = "https://www1.nseindia.com/products/dynaContent/equities/equities/json/online52NewHigh.json"
        self.year_low_url = "https://www1.nseindia.com/products/dynaContent/equities/equities/json/online52NewLow.json"
        self.preopen_nifty_url = "https://www1.nseindia.com/live_market/dynaContent/live_analysis/pre_open/nifty.json"
        self.preopen_fno_url = "https://www1.nseindia.com/live_market/dynaContent/live_analysis/pre_open/fo.json"
        self.preopen_niftybank_url = "https://www1.nseindia.com/live_market/dynaContent/live_analysis/pre_open/niftybank.json"
        self.fno_lot_size_url = "https://www1.nseindia.com/content/fo/fo_mktlots.csv"
        self.get_most_active__volume_url = "https://www1.nseindia.com/live_market/dynaContent/live_analysis/most_active/allTopVolume1.json"
        self.get_most_active__value_url = "https://www1.nseindia.com/live_market/dynaContent/live_analysis/most_active/allTopValue1.json"
        self.get_sector_url = "https://www1.nseindia.com/live_market/dynaContent/live_watch/stock_watch/{}StockWatch.json"
        self.get_option_chain_indices = (
            "https://www.nseindia.com/api/option-chain-indices?symbol={}"
        )
        self.get_option_chain_equities = (
            "https://www.nseindia.com/api/option-chain-equities?symbol={}"
        )
        self.baseurl = "https://www.nseindia.com/"

    def get_fno_lot_sizes(self, cached=True, as_json=False):
        """
        returns a dictionary with key as stock code and value as stock name.
        It also implements cache functionality and hits the server only
        if user insists or cache is empty
        :return: dict
        """
        url = self.fno_lot_size_url
        req = Request(url, None, self.headers)
        res_dict = {}
        if cached is not True or self.__CODECACHE__ is None:
            # raises HTTPError and URLError
            res = self.opener.open(req)
            if res is not None:
                # for py3 compat covert byte file like object to
                # string file like object
                res = byte_adaptor(res)
                for line in res.read().split("\n"):
                    if (
                        line != ""
                        and re.search(",", line)
                        and (line.casefold().find("symbol") == -1)
                    ):
                        (code, name) = [x.strip() for x in line.split(",")[1:3]]
                        res_dict[code] = int(name)
                    # else just skip the evaluation, line may not be a valid csv
            else:
                raise Exception("no response received")
            self.__CODECACHE__ = res_dict
        return self.render_response(self.__CODECACHE__, as_json)

    def get_stock_codes(self, cached=True, as_json=False):
        """
        returns a dictionary with key as stock code and value as stock name.
        It also implements cache functionality and hits the server only
        if user insists or cache is empty
        :return: dict
        """
        url = self.stocks_csv_url
        req = Request(url, None, self.headers)
        res_dict = {}
        if cached is not True or self.__CODECACHE__ is None:
            # raises HTTPError and URLError
            res = self.opener.open(req)
            if res is not None:
                # for py3 compat covert byte file like object to
                # string file like object
                res = byte_adaptor(res)
                for line in res.read().split("\n"):
                    if line != "" and re.search(",", line):
                        (code, name) = line.split(",")[0:2]
                        res_dict[code] = name
                    # else just skip the evaluation, line may not be a valid csv
            else:
                raise Exception("no response received")
            self.__CODECACHE__ = res_dict
        return self.render_response(self.__CODECACHE__, as_json)

    def is_valid_code(self, code):
        """
        :param code: a string stock code
        :return: Boolean
        """
        if code:
            stock_codes = self.get_stock_codes()
            if code.upper() in stock_codes.keys():
                return True
            else:
                return False

    def get_quote(self, code, as_json=False):
        """
        gets the quote for a given stock code
        :param code:
        :return: dict or None
        :raises: HTTPError, URLError
        """
        code = code.upper()
        if self.is_valid_code(code):
            url = self.build_url_for_quote(code)
            req = Request(url, None, self.headers)
            # this can raise HTTPError and URLError, but we are not handling it
            # north bound APIs should use it for exception handling
            res = self.opener.open(req)

            # for py3 compat covert byte file like object to
            # string file like object
            res = byte_adaptor(res)
            res = res.read()
            # Now parse the response to get the relevant data
            match = re.search(
                r'<div\s+id="responseDiv"\s+style="display:none">(.*?)</div>', res, re.S
            )
            try:
                buffer = match.group(1).strip()
                # commenting following two lines because now we are not using ast and instead
                # relying on json's ability to do parsing. Should be much faster and more
                # reliable.
                # buffer = js_adaptor(buffer)
                # response = self.clean_server_response(ast.literal_eval(buffer)['data'][0])
                response = self.clean_server_response(json.loads(buffer)["data"][0])
            except SyntaxError as err:
                raise Exception("ill formatted response")
            else:
                return self.render_response(response, as_json)
        else:
            return None

    def get_top_gainers(self, as_json=False):
        """
        :return: a list of dictionaries containing top gainers of the day
        """
        url = self.top_gainer_url
        req = Request(url, None, self.headers)
        # this can raise HTTPError and URLError
        res = self.opener.open(req)
        # for py3 compat covert byte file like object to
        # string file like object
        res = byte_adaptor(res)
        res_dict = json.load(res)
        # clean the output and make appropriate type conversions
        res_list = [self.clean_server_response(item) for item in res_dict["data"]]
        return self.render_response(res_list, as_json)

    def get_top_losers(self, as_json=False):
        """
        :return: a list of dictionaries containing top losers of the day
        """
        url = self.top_loser_url
        req = Request(url, None, self.headers)
        # this can raise HTTPError and URLError
        res = self.opener.open(req)
        # for py3 compat covert byte file like object to
        # string file like object
        res = byte_adaptor(res)
        res_dict = json.load(res)
        # clean the output and make appropriate type conversions
        res_list = [self.clean_server_response(item) for item in res_dict["data"]]
        return self.render_response(res_list, as_json)

    def get_top_fno_gainers(self, as_json=False):
        """
        :return: a list of dictionaries containing top gainers in fno of the day
        """
        url = self.top_fno_gainer_url
        req = Request(url, None, self.headers)
        # this can raise HTTPError and URLError
        res = self.opener.open(req)
        # for py3 compat covert byte file like object to
        # string file like object
        res = byte_adaptor(res)
        res_dict = json.load(res)
        # clean the output and make appropriate type conversions
        res_list = [self.clean_server_response(item) for item in res_dict["data"]]
        return self.render_response(res_list, as_json)

    def get_top_fno_losers(self, as_json=False):
        """
        :return: a list of dictionaries containing top losers of the day
        """
        url = self.top_fno_loser_url
        req = Request(url, None, self.headers)
        # this can raise HTTPError and URLError
        res = self.opener.open(req)
        # for py3 compat covert byte file like object to
        # string file like object
        res = byte_adaptor(res)
        res_dict = json.load(res)
        # clean the output and make appropriate type conversions
        res_list = [self.clean_server_response(item) for item in res_dict["data"]]
        return self.render_response(res_list, as_json)

    def get_advances_declines(self, as_json=False):
        """
        :return: a list of dictionaries with advance decline data
        :raises: URLError, HTTPError
        """
        url = self.advances_declines_url
        req = Request(url, None, self.headers)
        # raises URLError or HTTPError
        resp = self.opener.open(req)
        # for py3 compat covert byte file like object to
        # string file like object
        resp = byte_adaptor(resp)
        resp_dict = json.load(resp)
        resp_list = [self.clean_server_response(item) for item in resp_dict["data"]]
        return self.render_response(resp_list, as_json)

    def get_most_active(self, as_json=False, by="volume"):

        url = (
            self.get_most_active__volume_url
            if by == "volume"
            else self.get_most_active__value_url
        )
        req = Request(url, None, self.headers)
        # raises URLError or HTTPError
        resp = self.opener.open(req)
        # for py3 compat covert byte file like object to
        # string file like object
        resp = byte_adaptor(resp)
        resp_dict = json.load(resp)
        resp_list = [self.clean_server_response(item) for item in resp_dict["data"]]
        return self.render_response(resp_list, as_json)

    LOCATE_PY_DIRECTORY_PATH = os.path.abspath(os.path.dirname(__file__))

    def get_stocks_of_sector(self, as_json=False, sector="Nifty 50"):

        sectorkw = pd.read_csv(
            "{}/sectorKeywords.csv".format(self.LOCATE_PY_DIRECTORY_PATH)
        )
        sectorkw.set_index("Sector", inplace=True)
        url = self.get_sector_url.format(sectorkw.loc[sector].iloc[0])
        req = Request(url, None, self.headers)
        # raises URLError or HTTPError
        resp = self.opener.open(req)
        # for py3 compat covert byte file like object to
        # string file like object
        resp = byte_adaptor(resp)
        resp_dict = json.load(resp)
        resp_list = [self.clean_server_response(item) for item in resp_dict["data"]]
        return self.render_response(resp_list, as_json)

    def get_index_option_chain(self, index, as_json=False):

        url = self.get_option_chain_indices.format(index)
        headers = {
            "user-agent": "Chrome/80.0.3987.149 Safari/537.36",
            "accept-language": "en,gu;q=0.9,hi;q=0.8",
            "accept-encoding": "gzip, deflate, br",
        }
        session = requests.Session()
        request = session.get(self.baseurl, headers=headers, timeout=5)
        cookies = dict(request.cookies)
        response = session.get(url, headers=headers, timeout=5, cookies=cookies)
        # response =  requests.get(url, headers=self.headers)
        return response.json()

    def get_equity_option_chain(self, equity):
        
        url = self.get_option_chain_equities.format(equity)
        headers = {
            "user-agent": "Chrome/80.0.3987.149 Safari/537.36",
            "accept-language": "en,gu;q=0.9,hi;q=0.8",
            "accept-encoding": "gzip, deflate, br",
        }
        session = requests.Session()
        request = session.get(self.baseurl, headers=headers, timeout=5)
        cookies = dict(request.cookies)
        response = session.get(url, headers=headers, timeout=5, cookies=cookies)
        # response =  requests.get(url, headers=self.headers)
        return response.json()

    def get_index_list(self, as_json=False):
        """get list of indices and codes
        params:
            as_json: True | False
        returns: a list | json of index codes
        """

        url = self.index_url
        req = Request(url, None, self.headers)
        # raises URLError or HTTPError
        resp = self.opener.open(req)
        resp = byte_adaptor(resp)
        resp_list = json.load(resp)["data"]
        index_list = [str(item["name"]) for item in resp_list]
        return self.render_response(index_list, as_json)

    def get_active_monthly(self, as_json=False):
        return self._get_json_response_from_url(self.active_equity_monthly_url, as_json)

    def get_year_high(self, as_json=False):
        return self._get_json_response_from_url(self.year_high_url, as_json)

    def get_year_low(self, as_json=False):
        return self._get_json_response_from_url(self.year_low_url, as_json)

    def get_preopen_nifty(self, as_json=False):
        return self._get_json_response_from_url(self.preopen_nifty_url, as_json)

    def get_preopen_niftybank(self, as_json=False):
        return self._get_json_response_from_url(self.preopen_niftybank_url, as_json)

    def get_preopen_fno(self, as_json=False):
        return self._get_json_response_from_url(self.preopen_fno_url, as_json)

    def _get_json_response_from_url(self, url, as_json):
        """
        :return: a list of dictionaries containing the response got back from url
        """
        req = Request(url, None, self.headers)
        # this can raise HTTPError and URLError
        res = self.opener.open(req)
        # for py3 compat covert byte file like object to
        # string file like object
        res = byte_adaptor(res)
        res_dict = json.load(res)
        # clean the output and make appropriate type conversions
        res_list = [self.clean_server_response(item) for item in res_dict["data"]]
        return self.render_response(res_list, as_json)

    def is_valid_index(self, code):
        """
        returns: True | Flase , based on whether code is valid
        """
        index_list = self.get_index_list()
        return True if code.upper() in index_list else False

    def get_index_quote(self, code, as_json=False):
        """
        params:
            code : string index code
            as_json: True|False
        returns:
            a dict | json quote for the given index
        """
        url = self.index_url
        if self.is_valid_index(code):
            req = Request(url, None, self.headers)
            # raises HTTPError and URLError
            resp = self.opener.open(req)
            resp = byte_adaptor(resp)
            resp_list = json.load(resp)["data"]
            # this is list of dictionaries
            resp_list = [self.clean_server_response(item) for item in resp_list]
            # search the right list element to return
            search_flag = False
            for item in resp_list:
                if item["name"] == code.upper():
                    search_flag = True
                    break
            return self.render_response(item, as_json) if search_flag else None

    def nse_headers(self):
        """
        Builds right set of headers for requesting http://nseindia.com
        :return: a dict with http headers
        """
        return {
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.5",
            "Host": "www1.nseindia.com",
            "User-Agent": "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:28.0) Gecko/20100101 Firefox/28.0",
            "X-Requested-With": "XMLHttpRequest",
        }

    def nse_opener(self):
        """
        builds opener for urllib2
        :return: opener object
        """
        cj = CookieJar()
        return build_opener(HTTPCookieProcessor(cj))

    def build_url_for_quote(self, code):
        """
        builds a url which can be requested for a given stock code
        :param code: string containing stock code.
        :return: a url object
        """
        if code is not None and type(code) is str:
            encoded_args = urlencode(
                [
                    ("symbol", code),
                    ("illiquid", "0"),
                    ("smeFlag", "0"),
                    ("itpFlag", "0"),
                ]
            )
            return self.get_quote_url + encoded_args
        else:
            raise Exception("code must be string")

    def clean_server_response(self, resp_dict):
        """cleans the server reponse by replacing:
            '-'     -> None
            '1,000' -> 1000
        :param resp_dict:
        :return: dict with all above substitution
        """

        # change all the keys from unicode to string
        d = {}
        for key, value in resp_dict.items():
            d[str(key)] = value
        resp_dict = d
        for key, value in resp_dict.items():
            if type(value) is str or isinstance(value, six.string_types):
                if re.match("-", value):
                    try:
                        if float(value) or int(value):
                            dataType = True
                    except ValueError:
                        resp_dict[key] = None
                elif re.search(r"^[0-9,.]+$", value):
                    # replace , to '', and type cast to int
                    resp_dict[key] = float(re.sub(",", "", value))
                else:
                    resp_dict[key] = str(value)
        return resp_dict

    def render_response(self, data, as_json=False):
        if as_json is True:
            return json.dumps(data)
        else:
            return data

    def get_bhavcopy_url(self, d):
        """take date and return bhavcopy url"""
        d = mkdate(d)
        day_of_month = d.strftime("%d")
        mon = d.strftime("%b").upper()
        year = d.year
        url = self.bhavcopy_base_url % (year, mon, day_of_month, mon, year)
        return url

    def get_bhavcopy_filename(self, d):
        d = mkdate(d)
        day_of_month = d.strftime("%d")
        mon = d.strftime("%b").upper()
        year = d.year
        filename = self.bhavcopy_base_filename % (day_of_month, mon, year)
        return filename

    def download_bhavcopy(self, d):
        """returns bhavcopy as csv file."""
        # ex_url = "https://www.nseindia.com/content/historical/EQUITIES/2011/NOV/cm08NOV2011bhav.csv.zip"
        url = self.get_bhavcopy_url(d)
        filename = self.get_bhavcopy_filename(d)
        # response = requests.get(url, headers=self.headers)
        response = self.opener.open(Request(url, None, self.headers))
        zip_file_handle = io.BytesIO(response.read())
        zf = zipfile.ZipFile(zip_file_handle)
        try:
            result = zf.read(filename)
        except KeyError:
            result = zf.read(zf.filelist[0].filename)
        return zf.read(filename).decode("utf-8")

    def download_index_copy(self, d):
        """returns index copy file"""
        pass

    def __str__(self):
        """
        string representation of object
        :return: string
        """
        return "Driver Class for National Stock Exchange (NSE)"


if __name__ == "__main__":
    n = Nse()
    data = n.download_bhavcopy("14th Dec")

# TODO: get_most_active()
# TODO: get_top_volume()
# TODO: get_peer_companies()
# TODO: is_market_open()
# TODO: concept of portfolio for fetching price in a batch and field which should be captured
# TODO: Concept of session, just like as in sqlalchemy
