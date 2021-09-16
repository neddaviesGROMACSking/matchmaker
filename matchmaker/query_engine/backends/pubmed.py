from pydantic import BaseModel
from typing import List, Union, Literal

from matchmaker.query_engine.query_types import PaperSearchQuery, \
        AuthorSearchQuery, PaperDetailsQuery, AuthorDetailsQuery, CoauthorQuery
from matchmaker.query_engine.data_types import PaperData, AuthorData
from matchmaker.query_engine.slightly_less_abstract import SlightlyLessAbstractQueryEngine
from matchmaker.query_engine.backend import Backend



def make_search_given_term(
    term, 
    db='pubmed', 
    retmax:int = 10000, 
    prefix= 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/'
):
    return f'{prefix}esearch.fcgi?db={db}&retmax={retmax}&term={term}'

test = '(Jeremy Green[Author]) AND (Test[Title/Abstract])'


class PubMedPaperSearchQuery(BaseModel):
    term: str


class PubMedAuthorSearchQuery(BaseModel):
    # TODO: implement this
    pass


class PubMedPaperDetailsQuery(BaseModel):
    # TODO: implement this
    pass


class PubMedAuthorDetailsQuery(BaseModel):
    # TODO: implement this
    pass


class PubMedCoauthorsQuery(BaseModel):
    # TODO: implement this
    pass


class PubMedPaperData(BaseModel):
    # TODO: implement this
    pass


class PubMedAuthorData(BaseModel):
    # TODO: implement this
    pass


def paper_from_native(data):
    raise NotImplementedError('TODO')


class PaperSearchQueryEngine(
        SlightlyLessAbstractQueryEngine[PaperSearchQuery,
            List[PaperData], PubMedPaperSearchQuery, List[PubMedPaperData]]):
    def _query_to_native(self, query: PaperSearchQuery) -> PubMedPaperSearchQuery:
        def make_year_term(start_year:int = 1000, end_year:int = 3000):
            if start_year==end_year:
                return f'("{start_year}"[Date - Publication])'
            else:
                return f'("{start_year}"[Date - Publication] : "{end_year}"[Date - Publication])'
        def make_title_term(title:str):
            return f'({title}[Title])'
        def make_abstract_term(abstract_phrase:str):
            return f'({abstract_phrase}[Abstract])'
        def make_institution_term(institution:str):
            return f'({institution}[Affiliation])'
        def make_author_term(name:str):
            return f'({name}[Author])'
        def make_journal_term(journal_name: str):
            return f'({journal_name}[Journal])'
        def make_keyword_term(keyword: str):
            return f'({keyword}[Other Term])'
        
        query = query.dict()['query']

        def query_to_term(query):
            if query['tag'] == 'and':
                fields = query['fields_']
                return '('+' AND '.join([query_to_term(field) for field in fields])+')'
            elif query['tag'] == 'or':
                fields = query['fields_']
                return '('+' OR '.join([query_to_term(field) for field in fields])+')'
            elif query['tag'] == 'title':
                operator = query['operator']
                value = operator['value']
                return make_title_term(value)
            elif query['tag'] == 'author':
                operator = query['operator']
                value = operator['value']
                return make_author_term(value)
            elif query['tag'] == 'journal':
                operator = query['operator']
                value = operator['value']
                return make_journal_term(journal)
            elif query['tag'] == 'abstract':
                operator = query['operator']
                value = operator['value']
                return make_abstract_term(value)
            elif query['tag'] == 'institution':
                operator = query['operator']
                value = operator['value']
                return make_institution_term(value)
            elif query['tag'] == 'keyword':
                operator = query['operator']
                value = operator['value']
                return make_keyword_term(value)
            elif query['tag'] == 'year':
                operator = query['operator']
                if operator['tag'] =='equal':
                    value = operator['value']
                    return make_year_term(value,value)
                elif operator['tag'] == 'lt':
                    value = operator['value']
                    return make_year_term(end_year=value)
                elif operator['tag'] == 'gt':
                    value = operator['value']
                    return make_year_term(start_year=value)
                elif operator['tag'] == 'range':
                    lower_bound = operator['lower_bound']
                    upper_bound = operator['upper_bound']
                    return make_year_term(lower_bound,upper_bound)
                else:
                    raise ValueError('Unknown tag')
            else:
                raise ValueError('Unknown tag')
        
        term = query_to_term(query)
        return PubMedPaperSearchQuery(term=term)


    def _run_native_query(self, query: PubMedPaperSearchQuery) -> List[PubMedPaperData]:
        # TODO: implement this
        pass

    def _post_process(self, query: PaperSearchQuery, data: List[PubMedPaperData]) -> List[PubMedPaperData]:
        # TODO: implement this
        pass

    def _data_from_native(self, data: List[PubMedPaperData]) -> List[PaperData]:
        return [paper_from_native(datum) for datum in data]


class AuthorSearchQueryEngine(
        SlightlyLessAbstractQueryEngine[AuthorSearchQuery,
            List[AuthorData], PubMedAuthorSearchQuery, List[PubMedAuthorData]]):
    def _query_to_native(self, query: AuthorSearchQuery) -> PubMedAuthorSearchQuery:
        # TODO: implement this
        pass

    def _run_native_query(self, query: PubMedAuthorSearchQuery) -> List[PubMedAuthorData]:
        # TODO: implement this
        pass

    def _post_process(self, query: AuthorSearchQuery, data: List[PubMedAuthorData]) -> List[PubMedAuthorData]:
        # TODO: implement this
        pass

    def _data_from_native(self, data: List[PubMedAuthorData]) -> List[AuthorData]:
        # TODO: implement this
        pass


class PaperDetailsQueryEngine(
        SlightlyLessAbstractQueryEngine[PaperDetailsQuery,
            PaperData, PubMedPaperDetailsQuery, PubMedPaperData]):
    def _query_to_native(self, query: PaperDetailsQuery) -> PubMedPaperDetailsQuery:
        # TODO: implement this
        pass

    def _run_native_query(self, query: PubMedPaperDetailsQuery) -> PubMedPaperData:
        # TODO: implement this
        pass

    def _post_process(self, query: PaperDetailsQuery, data: PubMedPaperData) -> PubMedPaperData:
        # TODO: implement this
        pass

    def _data_from_native(self, data: PubMedPaperData) -> PaperData:
        return paper_from_native(data)


class AuthorDetailsQueryEngine(
        SlightlyLessAbstractQueryEngine[AuthorDetailsQuery,
            AuthorData, PubMedAuthorDetailsQuery, PubMedAuthorData]):
    def _query_to_native(self, query: AuthorDetailsQuery) -> PubMedAuthorDetailsQuery:
        # TODO: implement this
        pass

    def _run_native_query(self, query: PubMedAuthorDetailsQuery) -> PubMedAuthorData:
        # TODO: implement this
        pass

    def _post_process(self, query: AuthorDetailsQuery, data: PubMedAuthorData) -> PubMedAuthorData:
        # TODO: implement this
        pass

    def _data_from_native(self, data: PubMedAuthorData) -> AuthorData:
        # TODO: implement this
        pass


class CoauthorQueryEngine(
        SlightlyLessAbstractQueryEngine[CoauthorQuery,
            List[AuthorData], PubMedCoauthorsQuery, List[PubMedAuthorData]]):
    def _query_to_native(self, query: CoauthorQuery) -> PubMedCoauthorsQuery:
        # TODO: implement this
        pass

    def _run_native_query(self, query: PubMedCoauthorsQuery) -> List[PubMedAuthorData]:
        # TODO: implement this
        pass

    def _post_process(self, query: CoauthorQuery, data: List[PubMedAuthorData]) -> List[PubMedAuthorData]:
        # TODO: implement this
        pass

    def _data_from_native(self, data: List[PubMedAuthorData]) -> List[AuthorData]:
        # TODO: implement this
        pass


class PubMedBackend(Backend):
    def paperSearchEngine(self) -> PaperSearchQueryEngine:
        return PaperSearchQueryEngine()

    def authorSearchEngine(self) -> AuthorSearchQueryEngine:
        return AuthorSearchQueryEngine()

    def paperDetailsEngine(self) -> PaperDetailsQueryEngine:
        return PaperDetailsQueryEngine()

    def authorDetailsEngine(self) -> AuthorDetailsQueryEngine:
        return AuthorDetailsQueryEngine()

    def coauthorsEngine(self) -> CoauthorQueryEngine:
        return CoauthorQueryEngine()
