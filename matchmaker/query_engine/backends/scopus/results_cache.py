from pybliometrics.scopus.utils.constants import DEFAULT_PATHS
import csv
from typing import Optional


    
def get_no_results(search_name: str, query_string: str) -> Optional[int]:
    if search_name not in DEFAULT_PATHS:
        raise NotImplementedError # TODO Implement
    path_new = str(DEFAULT_PATHS[search_name]) + '/results_cache.csv'
    try:
        with open(path_new, 'r') as csvfile:
            file_reader = csv.reader(csvfile, delimiter=',')
            output = list(file_reader)
            if output == []:
                return None
            index = {}
            for row in output:
                index[row[0]] = row[1]
            
    except FileNotFoundError:
        return None

    try:
        no_results = index[query_string]
    except KeyError:
        return None
    return int(no_results)


def store_no_results(query_string: str, results) -> None:
    def store_no_results_in_cache_inner(search_name:str, query_string: str, no_results: int) -> None:
        if search_name not in DEFAULT_PATHS:
            raise NotImplementedError # TODO Implement
        path_new = str(DEFAULT_PATHS[search_name]) + '/results_cache.csv'
        with open(path_new, 'a+', newline='') as csvfile:
            file_writer = csv.writer(csvfile, delimiter=',')
            file_writer.writerow([str(query_string), str(no_results)])
    search_name = results.__class__.__name__

    no_results = results.get_results_size()
    existing_no_results = get_no_results(search_name, query_string)
    if existing_no_results is not None and no_results is not None:
        assert existing_no_results == no_results
    elif no_results is None:
        pass
    elif existing_no_results is None:
        store_no_results_in_cache_inner(search_name, query_string, no_results)
    else:
        pass
