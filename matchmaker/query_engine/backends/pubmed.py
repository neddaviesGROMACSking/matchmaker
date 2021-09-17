from pydantic import BaseModel
from typing import List, Union, Literal, Optional, Any

from matchmaker.query_engine.query_types import PaperSearchQuery, \
        AuthorSearchQuery, PaperDetailsQuery, AuthorDetailsQuery, CoauthorQuery
from matchmaker.query_engine.data_types import PaperData, AuthorData
from matchmaker.query_engine.slightly_less_abstract import SlightlyLessAbstractQueryEngine
from matchmaker.query_engine.backend import Backend

from urllib.parse import quote_plus
from urllib.request import urlopen
import xml.etree.ElementTree as xml_parse
import xmltodict
import requests
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

class PubmedTopic(BaseModel):
    descriptor: str
    qualifier: Optional[Union[str,List[str]]] = None

class PubmedIndividual(BaseModel):
    last_name: str
    fore_name: str
    initials: str

class PubmedCollective(BaseModel):
    collective_name:str


class PubmedAuthor(BaseModel):
    __root__: Union[PubmedIndividual, PubmedCollective]

class AbstractItem(BaseModel):
    label: Optional[str]
    nlm_category: Optional[str]
    text: Optional[str]

class PubMedPaperData(BaseModel):
    pubmed_id: str
    title: str
    year: Optional[int]
    author_list: List[PubmedAuthor]
    journal_title: str
    journal_title_abr: str
    institution: Optional[str]
    keywords: Optional[List[str]]
    topics: List[PubmedTopic]
    abstract: Optional[Union[str, List[AbstractItem]]]
    references: Optional[List[str]] = None
    cited_by: Optional[List[str]] = None




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

        def make_string_term(string, value, operator):
            if operator == 'in' and len(value) > 4:
                return f'({value}*[{string}])'
            elif operator == 'in':
                raise ValueError(f'Value {value} in section {string} too short for operator "in"')
            else:
                return f'({value}[{string}])'
            
        query = query.dict()['__root__']

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
                return make_string_term('Title', value, operator)
            elif query['tag'] == 'author':
                operator = query['operator']
                value = operator['value']
                return make_string_term('Author', value, operator)
            elif query['tag'] == 'journal':
                operator = query['operator']
                value = operator['value']
                return make_string_term('Journal', value, operator)
            elif query['tag'] == 'abstract':
                operator = query['operator']
                value = operator['value']
                return make_string_term('Abstract', value, operator)
            elif query['tag'] == 'institution':
                operator = query['operator']
                value = operator['value']
                return make_string_term('Affiliation', value, operator)
            
            elif query['tag'] == 'keyword':
                operator = query['operator']
                value = operator['value']
                return make_string_term('Other Term', value, operator)
            
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
        def make_search_given_term(
            term, 
            db='pubmed', 
            retmax:int = 10000, 
            prefix= 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/'
        ):
            return f'{prefix}esearch.fcgi?db={db}&retmax={retmax}&term={quote_plus(str(term))}'
        
        def make_fetch_given_ids(
            id_list,
            prefix= 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/'
        ):
            return f'{prefix}efetch.fcgi?db=pubmed&retmode=xml&id={",".join(id_list)}'

        def make_cited_by_given_ids(
            id_list,
            prefix= 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/'
        ):
            #https://eutils.ncbi.nlm.nih.gov/entrez/eutils/elink.fcgi?dbfrom=pubmed&linkname=pubmed_pubmed_citedin&id=21876726
            return f'{prefix}elink.fcgi?dbfrom=pubmed&linkname=pubmed_pubmed_citedin&id='+'&id='.join(id_list)
        
        def make_references_given_ids(
            id_list,
            prefix= 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/'
        ):
            #https://eutils.ncbi.nlm.nih.gov/entrez/eutils/elink.fcgi?dbfrom=pubmed&linkname=pubmed_pubmed_refs&id=24752654
            return f'{prefix}elink.fcgi?dbfrom=pubmed&linkname=pubmed_pubmed_refs&id='+'&id='.join(id_list)

        def proc_author(
            author_item
        ):
            if 'LastName' in author_item:
                return PubmedAuthor.parse_obj({
                    'last_name': author_item['LastName'], 
                    'fore_name': author_item['ForeName'],
                    'initials': author_item['Initials']
                })
            elif 'CollectiveName' in author_item:
                return PubmedAuthor.parse_obj({
                    'collective_name': author_item['CollectiveName']
                })

        def get_id_list_from_query(query):
            search_url = make_search_given_term(query.term)

            #test = urlopen(search_url).read()
            raw_out = requests.get(search_url).text
            proc_out = xmltodict.parse(raw_out)
            results = proc_out['eSearchResult']

            # Get metadata
            #count = results['Count']
            #ret_max = results['RetMax']
            #ret_start = results['RetStart']

            id_list_outer = results['IdList']
            id_list = id_list_outer['Id']
            return id_list


        def papers_from_id_list(id_list):
            fetch_url = make_fetch_given_ids(id_list)
            
            if len(id_list)>200:
                raw_fetch_out = requests.post(make_fetch_given_ids(['']), {'id': id_list}).text
            else:
                raw_fetch_out = requests.get(fetch_url).text
            
            proc_out = xmltodict.parse(raw_fetch_out)
            article_set = proc_out['PubmedArticleSet']['PubmedArticle']

            import json
            papers =[]
            for counter, i in enumerate(article_set):
                medline_citation=i['MedlineCitation']
                pubmed_id = medline_citation['PMID']['#text']
                final_structure= {}
                article = medline_citation['Article']
                try:
                    keywords = medline_citation['KeywordList']['Keyword']
                    keyword_text = [i['#text'] for i in keywords]
                except:
                    keywords = None
                    keyword_text=None
                
                topics = []
                if 'MeshHeadingList' in medline_citation:
                    mesh_headings = medline_citation['MeshHeadingList']['MeshHeading']
                    for mesh_heading in mesh_headings:
                        descriptor = mesh_heading['DescriptorName']['#text']
                        if 'QualifierName' in mesh_heading:
                            qualifier = mesh_heading['QualifierName']
                            if isinstance(qualifier, list):
                                new_qualifier = [i['#text'] for i in qualifier]
                            else:
                                new_qualifier = qualifier['#text']
                        else:
                            new_qualifier = None
                        topics.append(
                            PubmedTopic(descriptor= descriptor,qualifier = new_qualifier)
                        )
                
                journal = article['Journal']
                journal_title = journal['Title']
                journal_title_abr = journal['ISOAbbreviation']
                try:
                    year_pub = journal['JournalIssue']['PubDate']['Year']
                except:
                    year_pub = None


                title = article['ArticleTitle']
                try:
                    abstract = article['Abstract']['AbstractText']
                except:
                    abstract = None
                if isinstance(abstract, list):
                    new_abstract = []
                    for i in abstract:
                        if 'NlmCategory' in i:
                            nlm_cat = i['NlmCategory']
                        else:
                            nlm_cat = None
                        if '@Label' in i:
                            label = i['@Label']
                        else:
                            label = None
                        if '#text' in i:
                            text = i['#text']
                        else:
                            text = None
                        item = AbstractItem(
                            label = label,
                            nlm_category = nlm_cat,
                            text = text
                        )
                        new_abstract.append(item)
                else:
                    new_abstract = str(abstract)


                author_list = article['AuthorList']['Author']
                if isinstance(author_list, list):
                    author_list_proc = [proc_author(i) for i in author_list]
                    try:
                        institution = author_list[0]['AffiliationInfo']['Affiliation']
                    except:
                        institution = None
                else:
                    author_list_proc = [proc_author(author_list)]
                    try:
                        institution = author_list['AffiliationInfo']['Affiliation']
                    except:
                        institution = None

                print(title)
                paper_data = PubMedPaperData(
                    pubmed_id = pubmed_id,
                    title = title, 
                    year = year_pub,
                    author_list = author_list_proc,
                    journal_title = journal_title,
                    journal_title_abr = journal_title_abr,
                    institution = institution,
                    keywords = keyword_text,
                    topics = topics,
                    abstract = new_abstract
                )
                papers.append(paper_data)
                #print(json.dumps(paper_data.dict(),indent=2))
            return papers


        
        #print(ref_url)
        def get_linked_papers_given_url(url):
            raw_references = requests.get(url).text
            proc_ref = xmltodict.parse(raw_references)
            link_set = proc_ref['eLinkResult']['LinkSet']

            id_mapper = {}
            ref_fetch_list = []
            for link in link_set:
                id_value = link['IdList']['Id']
                if 'LinkSetDb' in link:
                    link_set_db = link['LinkSetDb']['Link']
                    link_proc = []
                    if isinstance(link_set_db, list):
                        link_proc = [i['Id'] for i in link_set_db]
                    else:
                        link_proc = [link_set_db['Id']]
                    #link_proc = [i['Id'] for i in link_set_db]
                    id_mapper[id_value] = link_proc
                    ref_fetch_list = ref_fetch_list + link_proc
                else:
                    id_mapper[id_value] = None
            unique_ref_fetch_list = list(set(ref_fetch_list))
            ref_papers = papers_from_id_list(unique_ref_fetch_list)
            ref_paper_index = {i.pubmed_id: i for i in ref_papers}

            id_mapper_papers = {}
            for search_id, id_list in id_mapper.items():
                if id_list is not None:
                    sub_papers = []
                    for sub_id in id_list:
                        paper = ref_paper_index[sub_id]
                        sub_papers.append(paper)
                    id_mapper_papers[search_id] = sub_papers
                else:
                    id_mapper_papers[search_id] = None
            return id_mapper_papers
        
        def get_references_from_id_list(id_list):
            ref_url = make_references_given_ids(id_list)
            return get_linked_papers_given_url(ref_url)
        
        def get_cited_by_from_id_list(id_list):
            cited_by_url = make_cited_by_given_ids(id_list)
            return get_linked_papers_given_url(cited_by_url)
        

        id_list = get_id_list_from_query(query)
        papers = papers_from_id_list(id_list)
        references_set = get_references_from_id_list(id_list)
        #cited_by_set = get_cited_by_from_id_list(id_list)

        for paper in papers:
            pubmed_id = paper.pubmed_id
            references = references_set[pubmed_id]
            paper.references = references
            #print(paper.dict())
        #print(ref_paper_index)
        #print(references)


        from pprint import pprint
        #pprint(references)

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
