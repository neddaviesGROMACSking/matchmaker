import csv
import time
from pybliometrics.scopus.utils.constants import DEFAULT_PATHS
from datetime import datetime

# Quote cache invariant - the reset time is the same throughout the file
def store_quota_in_cache(results):
    def store_quota_in_cache_inner(search_name: str, remaining: float, reset: float):
        if search_name not in DEFAULT_PATHS:
            raise NotImplementedError # TODO Implement
        path_new = str(DEFAULT_PATHS[search_name]) + '/quota_cache.csv'
        try:
            with open(path_new, 'r', newline='') as csvfile:
                file_reader = csv.reader(csvfile, delimiter=',')
                file_reader_list = list(file_reader)
                if file_reader_list !=[]:
                    reset_time_str = file_reader_list[0][1]
                    reset_time = time.mktime(datetime.strptime(reset_time_str, "%Y-%m-%d %H:%M:%S").timetuple())
                    current_time = time.time()
                    reset_file = float(reset_time) < current_time
                else:
                    reset_file = False
            if reset_file:
                with open(path_new, 'w+', newline='') as csvfile:
                    pass

        except FileNotFoundError:
            pass
        with open(path_new, 'a+', newline='') as csvfile:
            file_writer = csv.writer(csvfile, delimiter=',')
            file_writer.writerow([str(remaining), str(reset)])
    
    search_name = results.__class__.__name__
    reset = results.get_key_reset_time()
    remaining = results.get_key_remaining_quota()
    if reset is None or remaining is None:
        pass
        #raise ValueError('Reset and/or remaining not retrieved')
    else:
        store_quota_in_cache_inner(search_name, remaining, reset)

def _get_quota_in_cache_inner(search_name: str, index:int) -> str:
    if search_name not in DEFAULT_PATHS:
        raise NotImplementedError # TODO Implement
    path_new = str(DEFAULT_PATHS[search_name]) + '/quota_cache.csv'
    try:
        with open(path_new, 'r') as csvfile:
            file_reader = csv.reader(csvfile, delimiter=',')
            output = list(file_reader)
            if output == []:
                raise ValueError('Cache is empty!')
            
            min_remaining = None
            for row in output:
                if min_remaining is None:
                    min_remaining = row[index]
                else:
                    min_remaining = min(row[index], min_remaining)
    except FileNotFoundError:
        min_remaining = None
    if min_remaining is None:
        raise TypeError(f'{min_remaining} is None')
    return min_remaining
def get_remaining_in_cache(search_name: str) -> int:
    return int(_get_quota_in_cache_inner(search_name, 0))
def get_reset_in_cache(search_name: str) -> str:
    return _get_quota_in_cache_inner(search_name, 1)


"""
def get_scopus_key_reset_time_and_rem_quota(api_key,token, query = None):
    out = requests.get('https://api.elsevier.com/content/search/scopus?query=AUTHFIRST%28John%29+AND+AUTHLASTNAME%28Kitchin%29+AND+SUBJAREA%28COMP%29', headers = {"X-ELS-APIKey":api_key, "X-ELS-Insttoken": token})
    header_dict = dict(out.headers)
    return {
        "remaining": header_dict["X-RateLimit-Remaining"],
        "reset": header_dict["X-RateLimit-Reset"],
        "limit": header_dict["X-RateLimit-Limit"]
    }

def get_author_key_reset_time_and_rem_quota(api_key,token, query = None):
    out = requests.get('https://api.elsevier.com/content/search/author?query=AUTHFIRST%28John%29+AND+AUTHLASTNAME%28Kitchin%29+AND+SUBJAREA%28COMP%29', headers = {"X-ELS-APIKey":api_key, "X-ELS-Insttoken": token})
    header_dict = dict(out.headers)
    return {
        "remaining": header_dict["X-RateLimit-Remaining"],
        "reset": header_dict["X-RateLimit-Reset"],
        "limit": header_dict["X-RateLimit-Limit"]
    }

def get_affil_key_reset_time_and_rem_quota(api_key,token, query = None):
    out = requests.get('https://api.elsevier.com/content/search/affiliation?query=AFFIL(Kings College London)', headers = {"X-ELS-APIKey":api_key, "X-ELS-Insttoken": token})
    header_dict = dict(out.headers)
    return {
        "remaining": header_dict["X-RateLimit-Remaining"],
        "reset": header_dict["X-RateLimit-Reset"],
        "limit": header_dict["X-RateLimit-Limit"]
    }
"""