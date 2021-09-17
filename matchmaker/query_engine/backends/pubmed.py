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
            return f'{prefix}elink.fcgi?dbfrom=pubmed&linkname=pubmed_pubmed_citedin&id='+'&id='.join(id_list)
        
        def make_references_given_ids(
            id_list,
            prefix= 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/'
        ):
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

            raw_out = requests.get(search_url).text
            proc_out = xml_parse.fromstring(raw_out)
            id_list = []
            for result in proc_out:
                if result.tag == 'IdList':
                    id_list = id_list + [i.text for i in result.iterfind('Id')]

            # Get metadata
            #count = results['Count']
            #ret_max = results['RetMax']
            #ret_start = results['RetStart']

            return id_list


        def papers_from_id_list(id_list):
            fetch_url = make_fetch_given_ids(id_list)
            
            if len(id_list)>200:
                raw_fetch_out = requests.post(make_fetch_given_ids(['']), {'id': id_list}).text
            else:
                raw_fetch_out = requests.get(fetch_url).text
            proc_out = xml_parse.fromstring(raw_fetch_out)
            papers = []
            for i in proc_out:
                medline_citation = i.find('MedlineCitation')
                pubmed_id = medline_citation.find('PMID').text
                article = medline_citation.find('Article')

                keywordlist = medline_citation.find('KeywordList')
                if keywordlist is not None:
                    keyword_text = [i.text for i in keywordlist.findall('Keyword')]
                else:
                    keyword_text = None
                topics = []

                mesh_headings = medline_citation.find('MeshHeadingList')
                if mesh_headings is not None:
                    mesh_heading_list = mesh_headings.findall('MeshHeading')
                    for mesh_heading in mesh_heading_list:
                        descriptor = mesh_heading.find('DescriptorName').text
                        qualifier = mesh_heading.find('QualifierName')
                        if qualifier is not None:
                            if isinstance(qualifier, list):
                                new_qualifier = [j.text for j in qualifier]
                            else:
                                new_qualifier = qualifier.text
                        else:
                            new_qualifier = None
                        topics.append(
                            PubmedTopic(descriptor= descriptor,qualifier = new_qualifier)
                        )
                journal = article.find('Journal')
                journal_title = journal.find('Title').text
                journal_title_abr = journal.find('ISOAbbreviation').text
                year_pub_list = [i for i in journal.iter('Year')]
                if len(year_pub_list) == 1:
                    year_pub = year_pub_list[0].text
                else:
                    year_pub = None
                title = ' '.join(article.find('ArticleTitle').itertext())
                abstract = article.find('Abstract')
                if abstract is not None:
                    abstract_text_list = abstract.findall('AbstractText')
                    new_abstract = []
                    for abstract_text in abstract_text_list:
                        if 'Label' in abstract_text.attrib:
                            label = abstract_text.attrib['Label']
                        else:
                            label = None
                        if 'NlmCategory' in abstract_text.attrib:
                            nlm_cat = abstract_text.attrib['NlmCategory']
                        else:
                            nlm_cat = None
                        text = abstract_text.text

                        item = AbstractItem(
                            label = label,
                            nlm_category = nlm_cat,
                            text = text
                        )
                        new_abstract.append(item)

                author_list = article.iter("Author")
                #print(author_list)
                author_list_proc = []
                for author in author_list:
                    last_name_elem = author.find('LastName')
                    if last_name_elem is None:
                        collective = author.find('CollectiveName').text
                        author_final = PubmedAuthor.parse_obj({
                            'collective_name': collective
                        })
                    else:
                        last_name = last_name_elem.text
                        fore_name = author.find('ForeName').text
                        initials = author.find('Initials').text
                        author_final = PubmedAuthor.parse_obj({
                            'last_name': last_name, 
                            'fore_name': fore_name,
                            'initials': initials
                        })
                    author_list_proc.append(author_final)
                #print(author_list_proc)
                    
                    
                affiliation_info_list = [i for i in article.iter("AffiliationInfo")]
                if len(affiliation_info_list) ==1:
                    institution = affiliation_info_list[0].find('Affiliation').text
                else:
                    institution = None

                
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

        from pprint import pprint

        id_list = get_id_list_from_query(query)
        papers = papers_from_id_list(id_list)
        references_set = get_references_from_id_list(id_list)
        cited_by_set = get_cited_by_from_id_list(id_list)

        for paper in papers:
            pubmed_id = paper.pubmed_id
            references = references_set[pubmed_id]
            paper.references = references
            cited_by = cited_by_set[pubmed_id]
            paper.cited_by = cited_by
            #print()
            #pprint(paper.dict())

        return papers

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
