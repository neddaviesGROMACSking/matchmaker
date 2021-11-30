from collections import defaultdict
from gensim import corpora
from typing import List, Set
from gensim import models
from gensim import similarities
from matchmaker import query_engine
import numpy as np

import hashlib

def hash_string(string:str) -> int:
    return int(hashlib.sha1(string.encode("utf-8")).hexdigest(), 16) % (10 ** 8)
    
def produce_similarities(
    abstract_set1: List[str], 
    abstract_set2: List[str],
    excluded_words: Set[str],
    remove_singleton_words: bool = True) -> np.ndarray:

    def generate_texts(abstracts: List[str], excluded_words: Set[str], remove_singleton_words: bool = True) -> List[List[str]]:
        # remove common words and tokenise
        texts = [
            [word for word in document.lower().split() if word not in excluded_words]
            for document in abstracts
        ]
        texts = [
            [''.join(l for l in word if l.isalnum() or l==' ') for word in text if word not in excluded_words]
            for text in texts
        ]

        if remove_singleton_words:
            # remove words that appear only once
            frequency = defaultdict(int)
            for text in texts:
                for token in text:
                    frequency[token] += 1

            texts = [
                [token for token in text if frequency[token] > 1]
                for text in texts
            ]
        return texts

    def texts_to_hash(texts: List[List[str]]) -> str:
        combined_set = []
        for text in texts:
            combined_set += text
        
        combined_set = ''.join(combined_set)
        hash_value = str(abs(hash_string(combined_set)))
        return hash_value

    texts = generate_texts(abstract_set1, excluded_words, remove_singleton_words=remove_singleton_words)
    dictionary = corpora.Dictionary(texts)
    corpus = [dictionary.doc2bow(text) for text in texts]
    lsi = models.LsiModel(corpus, id2word=dictionary, num_topics=2)

    """
    # TODO Fix bug in cache
    hash_value = texts_to_hash(texts)
    try:
        index = similarities.MatrixSimilarity.load(f'/tmp/{hash_value}.index')
    except FileNotFoundError:
        index = similarities.MatrixSimilarity(lsi[corpus]) # transform corpus to LSI space and index it
        index.save(f'/tmp/{hash_value}.index')
    """
    index = similarities.MatrixSimilarity(lsi[corpus])
    
    vec_bow_texts = generate_texts(abstract_set2, excluded_words, remove_singleton_words=remove_singleton_words)
    vec_corpus = [dictionary.doc2bow(vec_bow_text) for vec_bow_text in vec_bow_texts] 
    vec_lsi = lsi[vec_corpus]  # convert the query to LSI space
    sims = index[vec_lsi]  # perform a similarity query against the corpus
    return sims

most_common = ['a','ability','able','about','above','accept','according','account','across','act','action','activity','actually','add','address','administration','admit','adult','affect','after','again','against','age','agency','agent','ago','agree','agreement','ahead','air','all','allow','almost','alone','along','already','also','although','always','American','among','amount','analysis','and','animal','another','answer','any','anyone','anything','appear','apply','approach','area','argue','arm','around','arrive','art','article','artist','as','ask','assume','at','attack','attention','attorney','audience','author','authority','available','avoid','away','baby','back','bad','bag','ball','bank','bar','base','be','beat','beautiful','because','become','bed','before','begin','behavior','behind','believe','benefit','best','better','between','beyond','big','bill','billion','bit','black','blood','blue','board','body','book','born','both','box','boy','break','bring','brother','budget','build','building','business','but','buy','by','call','camera','campaign','can','cancer','candidate','capital','car','card','care','career','carry','case','catch','cause','cell','center','central','century','certain','certainly','chair','challenge','chance','change','character','charge','check','child','choice','choose','church','citizen','city','civil','claim','class','clear','clearly','close','coach','cold','collection','college','color','come','commercial','common','community','company','compare','computer','concern','condition','conference','Congress','consider','consumer','contain','continue','control','cost','could','country','couple','course','court','cover','create','crime','cultural','culture','cup','current','customer','cut','dark','data','daughter','day','dead','deal','death','debate','decade','decide','decision','deep','defense','degree','Democrat','democratic','describe','design','despite','detail','determine','develop','development','die','difference','different','difficult','dinner','direction','director','discover','discuss','discussion','disease','do','doctor','dog','door','down','draw','dream','drive','drop','drug','during','each','early','east','easy','eat','economic','economy','edge','education','effect','effort','eight','either','election','else','employee','end','energy','enjoy','enough','enter','entire','environment','environmental','especially','establish','even','evening','event','ever','every','everybody','everyone','everything','evidence','exactly','example','executive','exist','expect','experience','expert','explain','eye','face','fact','factor','fail','fall','family','far','fast','father','fear','federal','feel','feeling','few','field','fight','figure','fill','film','final','finally','financial','find','fine','finger','finish','fire','firm','first','fish','five','floor','fly','focus','follow','food','foot','for','force','foreign','forget','form','former','forward','four','free','friend','from','front','full','fund','future','game','garden','gas','general','generation','get','girl','give','glass','go','goal','good','government','great','green','ground','group','grow','growth','guess','gun','guy','hair','half','hand','hang','happen','happy','hard','have','he','head','health','hear','heart','heat','heavy','help','her','here','herself','high','him','himself','his','history','hit','hold','home','hope','hospital','hot','hotel','hour','house','how','however','huge','human','hundred','husband','I','idea','identify','if','image','imagine','impact','important','improve','in','include','including','increase','indeed','indicate','individual','industry','information','inside','instead','institution','interest','interesting','international','interview','into','investment','involve','is', 'issue','it','item','its','itself','job','join','just','keep','key','kid','kill','kind','kitchen','know','knowledge','land','language','large','last','late','later','laugh','law','lawyer','lay','lead','leader','learn','least','leave','left','leg','legal','less','let','letter','level','lie','life','light','like','likely','line','list','listen','little','live','local','long','look','lose','loss','lot','love','low','machine','magazine','main','maintain','major','majority','make','man','manage','management','manager','many','market','marriage','material','matter','may','maybe','me','mean','measure','media','medical','meet','meeting','member','memory','mention','message','method','middle','might','military','million','mind','minute','miss','mission','model','modern','moment','money','month','more','morning','most','mother','mouth','move','movement','movie','Mr','Mrs','much','music','must','my','myself','name','nation','national','natural','nature','near','nearly','necessary','need','network','never','new','news','newspaper','next','nice','night','no','none','nor','north','not','note','nothing','notice','now','number','occur','of','off','offer','office','officer','official','often','oh','oil','ok','old','on','once','one','only','onto','open','operation','opportunity','option','or','order','organization','other','others','our','out','outside','over','own','owner','page','pain','painting','paper','parent','part','participant','particular','particularly','partner','party','pass','past','patient','pattern','pay','peace','people','per','perform','performance','perhaps','period','person','personal','phone','physical','pick','picture','piece','place','plan','plant','play','player','PM','point','police','policy','political','politics','poor','popular','population','position','positive','possible','power','practice','prepare','present','president','pressure','pretty','prevent','price','private','probably','problem','process','produce','product','production','professional','professor','program','project','property','protect','prove','provide','public','pull','purpose','push','put','quality','question','quickly','quite','race','radio','raise','range','rate','rather','reach','read','ready','real','reality','realize','really','reason','receive','recent','recently','recognize','record','red','reduce','reflect','region','relate','relationship','religious','remain','remember','remove','report','represent','Republican','require','research','resource','respond','response','responsibility','rest','result','return','reveal','rich','right','rise','risk','road','rock','role','room','rule','run','safe','same','save','say','scene','school','science','scientist','score','sea','season','seat','second','section','security','see','seek','seem','sell','send','senior','sense','series','serious','serve','service','set','seven','several','sex','sexual','shake','share','she','shoot','short','shot','should','shoulder','show','side','sign','significant','similar','simple','simply','since','sing','single','sister','sit','site','situation','six','size','skill','skin','small','smile','so','social','society','soldier','some','somebody','someone','something','sometimes','son','song','soon','sort','sound','source','south','southern','space','speak','special','specific','speech','spend','sport','spring','staff','stage','stand','standard','star','start','state','statement','station','stay','step','still','stock','stop','store','story','strategy','street','strong','structure','student','study','stuff','style','subject','success','successful','such','suddenly','suffer','suggest','summer','support','sure','surface','system','table','take','talk','task','tax','teach','teacher','team','technology','television','tell','ten','tend','term','test','than','thank','that','the','their','them','themselves','then','theory','there','these','they','thing','think','third','this','those','though','thought','thousand','threat','three','through','throughout','throw','thus','time','to','today','together','tonight','too','top','total','tough','toward','town','trade','traditional','training','travel','treat','treatment','tree','trial','trip','trouble','TRUE','truth','try','turn','TV','two','type','under','understand','unit','until','up','upon','us','use','usually','value','various','very','victim','view','violence','visit','voice','vote','wait','walk','wall','want','war','watch','water','way','we','weapon','wear','week','weight','well','west','western','what','whatever','when','where','whether','which','while','white','who','whole','whom','whose','why','wide','wife','will','win','wind','window','wish','with','within','without','woman','wonder','word','work','worker','world','worry','would','write','writer','wrong','yard','yeah','year','yes','yet','you','young','your','yourself']
most_common2 = ['a','able','about','above','act','add','afraid','after','again','against','age','ago','agree','air','all','allow','also','always','am','among','an','and','anger','animal','answer','any','appear','apple','are','area','arm','arrange','arrive','art','as','ask','at','atom','baby','back','bad','ball','band','bank','bar','base','basic','bat','be','bear','beat','beauty','bed','been','before','began','begin','behind','believe','bell','best','better','between','big','bird','bit','black','block','blood','blow','blue','board','boat','body','bone','book','born','both','bottom','bought','box','boy','branch','bread','break','bright','bring','broad','broke','brother','brought','brown','build','burn','busy','but','buy','by','call','came','camp','can','capital','captain','car','card','care','carry','case','cat','catch','caught','cause','cell','cent','center','century','certain','chair','chance','change','character','charge','chart','check','chick','chief','child','children','choose','chord','circle','city','claim','class','clean','clear','climb','clock','close','clothe','cloud','coast','coat','cold','collect','colony','color','column','come','common','company','compare','complete','condition','connect','consider','consonant','contain','continent','continue','control','cook','cool','copy','corn','corner','correct','cost','cotton','could','count','country','course','cover','cow','crease','create','crop','cross','crowd','cry','current','cut','dad','dance','danger','dark','day','dead','deal','dear','death','decide','decimal','deep','degree','depend','describe','desert','design','determine','develop','dictionary','did','die','differ','difficult','direct','discuss','distant','divide','division','do','doctor','does','dog','dollar','don’t','done','door','double','down','draw','dream','dress','drink','drive','drop','dry','duck','during','each','ear','early','earth','ease','east','eat','edge','effect','egg','eight','either','electric','element','else','end','enemy','energy','engine','enough','enter','equal','equate','especially','even','evening','event','ever','every','exact','example','except','excite','exercise','expect','experience','experiment','eye','face','fact','fair','fall','family','famous','far','farm','fast','fat','father','favor','fear','feed','feel','feet','fell','felt','few','field','fig','fight','figure','fill','final','find','fine','finger','finish','fire','first','fish','fit','five','flat','floor','flow','flower','fly','follow','food','foot','for','force','forest','form','forward','found','four','fraction','free','fresh','friend','from','front','fruit','full','fun','game','garden','gas','gather','gave','general','gentle','get','girl','give','glad','glass','go','gold','gone','good','got','govern','grand','grass','gray','great','green','grew','ground','group','grow','guess','guide','gun','had','hair','half','hand','happen','happy','hard','has','hat','have','he','head','hear','heard','heart','heat','heavy','held','help','her','here','high','hill','him','his','history','hit','hold','hole','home','hope','horse','hot','hot','hour','house','how','huge','human','hundred','hunt','hurry','I','ice','idea','if','imagine','in','inch','include','indicate','industry','insect','instant','instrument','interest','invent','iron','is','island','it','job','join','joy','jump','just','keep','kept','key','kill','kind','king','knew','know','lady','lake','land','language','large','last','late','laugh','law','lay','lead','learn','least','leave','led','left','leg','length','less','let','letter','level','lie','life','lift','light','like','line','liquid','list','listen','little','live','locate','log','lone','long','look','lost','lot','loud','love','low','machine','made','magnet','main','major','make','man','many','map','mark','market','mass','master','match','material','matter','may','me','mean','meant','measure','meat','meet','melody','men','metal','method','middle','might','mile','milk','million','mind','mine','minute','miss','mix','modern','molecule','moment','money','month','moon','more','morning','most','mother','motion','mount','mountain','mouth','move','much','multiply','music','must','my','name','nation','natural','nature','near','necessary','neck','need','neighbor','never','new','next','night','nine','no','noise','noon','nor','north','nose','note','nothing','notice','noun','now','number','numeral','object','observe','occur','ocean','of','off','offer','office','often','oh','oil','old','on','once','one','only','open','operate','opposite','or','order','organ','original','other','our','out','over','own','oxygen','page','paint','pair','paper','paragraph','parent','part','particular','party','pass','past','path','pattern','pay','people','perhaps','period','person','phrase','pick','picture','piece','pitch','place','plain','plan','plane','planet','plant','play','please','plural','poem','point','poor','populate','port','pose','position','possible','post','pound','power','practice','prepare','present','press','pretty','print','probable','problem','process','produce','product','proper','property','protect','prove','provide','pull','push','put','quart','question','quick','quiet','quite','quotient','race','radio','rail','rain','raise','ran','range','rather','reach','read','ready','real','reason','receive','record','red','region','remember','repeat','reply','represent','require','rest','result','rich','ride','right','ring','rise','river','road','rock','roll','room','root','rope','rose','round','row','rub','rule','run','safe','said','sail','salt','same','sand','sat','save','saw','say','scale','school','science','score','sea','search','season','seat','second','section','see','seed','seem','segment','select','self','sell','send','sense','sent','sentence','separate','serve','set','settle','seven','several','shall','shape','share','sharp','she','sheet','shell','shine','ship','shoe','shop','shore','short','should','shoulder','shout','show','side','sight','sign','silent','silver','similar','simple','since','sing','single','sister','sit','six','size','skill','skin','sky','slave','sleep','slip','slow','small','smell','smile','snow','so','soft','soil','soldier','solution','solve','some','son','song','soon','sound','south','space','speak','special','speech','speed','spell','spend','spoke','spot','spread','spring','square','stand','star','start','state','station','stay','stead','steam','steel','step','stick','still','stone','stood','stop','store','story','straight','strange','stream','street','stretch','string','strong','student','study','subject','substance','subtract','success','such','sudden','suffix','sugar','suggest','suit','summer','sun','supply','support','sure','surface','surprise','swim','syllable','symbol','system','table','tail','take','talk','tall','teach','team','teeth','tell','temperature','ten','term','test','than','thank','that','the','their','them','then','there','these','they','thick','thin','thing','think','third','this','those','though','thought','thousand','three','through','throw','thus','tie','time','tiny','tire','to','together','told','tone','too','took','tool','top','total','touch','toward','town','track','trade','train','travel','tree','triangle','trip','trouble','truck','try','tube','turn','twenty','two','type','under','unit','until','up','us','use','usual','valley','value','vary','verb','very','view','village','visit','voice','vowel','wait','walk','wall','want','war','warm','was','wash','watch','water','wave','way','we','wear','weather','week','weight','well','went','were','west','what','wheel','when','where','whether','which','while','white','who','whole','whose','why','wide','wife','wild','will','win','wind','window','wing','winter','wire','wish','with','woman','women','won’t','wonder','wood','word','work','world','would','write','written','wrong','wrote','yard','year','yellow','yes','yet','you','young','your']
others = ['', 'into', 'not', 'elsevier', '©', 'is', 'thus', '-']
letters = ['a','b','c','d','e','f','g','h','i','j','k','l','m','n','o','p','q','r','s','t','u','v','w','x','y','z']
numbers = list(map(str, list(range(100))))

most_common_abstract_words = 'language English planning policy French linguistic English planning policy linguistic linguistic English planning problem education education national political identity policy officialpolitical ethnic political development national African economic development world status French social regional group status speakers speakers economic speech status development social indigenous national bilingual public Greek government Spanish international group cultural official history identity Arabic'.split(' ')
total = most_common+most_common2+others+letters+ numbers+ most_common_abstract_words

def calculate_directional_set_similarity(
    abstract_set1: List[str], 
    abstract_set2: List[str]
) -> float:
    def get_doc_count_bias(abstract_set1, power = 1):
        count = len(abstract_set1)
        return 1-count**-power
    set1_bias = get_doc_count_bias(abstract_set1)
    set2_bias = get_doc_count_bias(abstract_set2)
    overall_bias = set1_bias * set2_bias
    excluded_words = set(total)
    similarity_matrix = produce_similarities(
        abstract_set1,
        abstract_set2,
        excluded_words,
        remove_singleton_words=True
    )
    """
    def get_match_rating(similarity_matrix):
        def get_values_array(similarity_matrix):
            output_list = []
            for i in similarity_matrix:
                for j in i:
                    if j > 0:
                        output_list.append(j)
            dtype = [('Match', float)]
            values_array = np.sort(np.array(output_list, dtype = dtype),order='Match')
            return values_array
        values_array = get_values_array(similarity_matrix)
        from scipy.optimize import curve_fit
        ydata = values_array
        xdata = np.array(list(range(len(values_array))))

        
        def objective(x, a, b, c):
            return b - a/(x+c)

        popt, pcov = curve_fit(
            objective, 
            xdata, 
            ydata, 
            bounds = ([0.00001, 0.00001, 0.00001], [np.inf, np.inf,np.inf]), 
            p0=np.asarray([100,1,100]) 
        )
        perr = np.sqrt(np.diag(pcov))
        print('a: ', popt[0], '+-', perr[0])
        print('b: ', popt[1], '+-', perr[1])
        print('c: ', popt[2], '+-', perr[2])
        
        import matplotlib.pyplot as plt
        plt.plot(xdata, ydata, 'b-', label='data')

        new_ydata = objective(xdata, *popt)
        plt.plot(xdata, new_ydata, 'r-',
                label='fit: a=%5.3f, b=%5.3f, c=%5.3f' % tuple(popt))
        plt.xlabel('x')
        plt.ylabel('y')
        plt.legend()
        plt.savefig("mygraph.png")
        plt.close()
        match = objective(popt[0], 500, 1,0)
        print('Match: ',match)

    """
    #q75, q25 = np.percentile(similarity_matrix, [75 ,25])
    #within_interquartile = np.logical_and(similarity_matrix> q25, similarity_matrix< q75)
    #return np.average(similarity_matrix[within_interquartile])
    #return np.average(np.power(similarity_matrix,2))
    """
    new_test = np.zeros(similarity_matrix.shape, dtype = 'float32')
    for i, el in enumerate(similarity_matrix):
        new_test[i] = el
    test = new_test.flatten()
    

    with open('dist.txt', 'w+') as f:
        for i in list(similarity_matrix):
            for j in i:
                f.write(str(j) + "\n")
    """
    #get_match_rating(similarity_matrix)
    return np.average(similarity_matrix) #* overall_bias

def calculate_set_similarity(
    abstract_set1: List[str], 
    abstract_set2: List[str]
) -> float:
    if abstract_set1 ==[] or abstract_set2 == []:
        return 0
    value1 = calculate_directional_set_similarity(abstract_set1, abstract_set2)
    value2 = calculate_directional_set_similarity(abstract_set2, abstract_set1)
    return (value1+value2)/2



