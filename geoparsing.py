import numpy as np
import string 
from collections import namedtuple
from shapely import wkt
from shapely.ops import unary_union
from pyproj import Geod
from collections import defaultdict
from bigtree import  print_tree, list_to_tree
from itertools import groupby
import spacy
from joblib import Parallel, delayed
import pandas as pd 
import spacy
import geopandas as gpd
from OSMPythonTools.nominatim import Nominatim

LOC = namedtuple('LOC', ['loc', 'displayName', 'geometry', 'area'])
geod = Geod(ellps="WGS84")
finder = Nominatim()


def ponctuationfree(text) -> string:
    return text.translate(text.maketrans(string.punctuation, ' '*len(string.punctuation)))
    

def safe_join(row: list, columns:list) -> string:
    l = [ponctuationfree(text) for text in [row[column] for column in columns] if text is not None]
    return " , ".join(l)

def defaultvalue(loc:string, wkt_=False) -> namedtuple:
    query = finder.query(loc, wkt=wkt_)
    displayName = query.displayName()
    if displayName is not None and wkt_:
        geometry = wkt.loads(query.wkt())
        if geometry is not None and geometry.is_valid:
            area = abs(geod.geometry_area_perimeter(geometry)[0])/1e6
        else :
            area = None
    else :
        geometry, area = None, None
    return LOC(loc, displayName, geometry, area)

def cleaning_geometry(geometry):
    if geometry is not None:
        if 'polygon' not in geometry.type.lower():
            return geometry.convex_hull
        else :
            return geometry
    else :
        return geometry

def safe_le(a, b):
    if b is None or a is None:
        return True
    else :
        return a <= b

def geocode_root(country:str)->str:
    l_country = country.split(';')
    return ";".join([defaultvalue(country).displayName.replace('/','-') for country in l_country ])

def safe_ge(a, b):
    if b is None or a is None:
        return True
    else :
        return a >= b

class OSMGeoParser():

    def __init__(self, area_threshold_low = None, area_threshold_high = None):
        self.dlocs = {}
        self.dleaf_loc = {}
        self.area_threshold_low = area_threshold_low
        self.area_threshold_high = area_threshold_high


    def from_dataframe(self, dataframe: pd.DataFrame, columns:list, root_in=None, union=True, wrapper=None,
      n_jobs=-1, prefer='threads') -> gpd.GeoDataFrame:

        """

        - wrapper: func, default : None 
            wrapper is used to filter the row  of the dataframe on
            which the geoparsing is done. It can be also used to process the texts inside the columns.

            -> Mandatory : it should take as input : a row and the name of the columns on which to 
            perform the geoparsing. It should return a string (Empty string to not perform the
            geoparsing). 

            a typical wrapper :

            def wrapper_safe_join(row, columns=list):
                if len(row.country.split(';')) < 4:
                    return safe_join(row, columns=columns)
                else :
                    return ''

            If None, the wrapper is simply the function safe_join that remove the ponctuation
            of each column before joining the strings on ','. 

        -----------------------------------
        Returns:
            _type_: GeoPandas.GeoDataFrame
                """

        if wrapper is None:
            wrapper = safe_join 

        #caution 
        for column in columns:
            dataframe[column] = dataframe[column].astype(str)

        texts = dataframe.apply(lambda row:wrapper(row, columns=columns), axis=1).to_list()

        geometry = self.geoparse_list(texts, n_jobs=n_jobs, prefer=prefer, union=union,\
             index=dataframe.index)
        dataframe['join_index'] = dataframe.index
        data = dataframe.merge(geometry, on='join_index', validate='one_to_many')

        gdf = gpd.GeoDataFrame(data, geometry='geometry', crs='epsg:4326')
        if root_in is not None and root_in in gdf.columns:
            gdf['root_in'] = gdf[root_in].apply(geocode_root)
            gdf['valid'] = gdf.apply(lambda x:x.root in x.root_in, axis=1)
            gdf = gdf[ gdf.valid ]

        conversion_rate = gdf.dropna(subset='geometry').drop_duplicates(subset='join_index').shape[0] / dataframe.shape[0]
        print(f'conversion rate : {conversion_rate :.2%}')

        gdf['geometry'] = gdf['geometry'].apply(cleaning_geometry)
        return gdf



    def geoparse_list(self, texts:list, n_jobs=-1, prefer='threads', union=True, index=None, 
    NER = ['LOC', 'GPE']) -> list:
        nlp = spacy.load("xx_ent_wiki_sm", enable=['ner'])

        #Entity recognition
        docs = list(nlp.pipe(texts))

        #Retrieving LOC
        self.l_entities = []
        for doc in docs:
            entities = {key: list(g) for key, g in groupby(sorted(doc.ents, key=lambda x: x.label_), lambda x: x.label_)}
            ents = []
            for ner in NER:
                if ner in entities.keys():
                    ents.extend(entities[ner])
    
            if len(ents) == 0:
                self.l_entities.append(None)
            else:
                self.l_entities.append(ents)

        #GeoParsing
        if index is not None:
            gdfs = Parallel(n_jobs=n_jobs, prefer=prefer, verbose=5)\
                (delayed(self.osm_research)(locs, printtree=False, union=union, index=i) \
                    for i,locs in zip(index,self.l_entities))
        else:
            gdfs = Parallel(n_jobs=n_jobs, prefer=prefer, verbose=5)\
                (delayed(self.osm_research)(locs, printtree=False, union=union) for locs in self.l_entities)
            
        return gpd.GeoDataFrame(pd.concat(gdfs), geometry='geometry', crs='epsg:4326') 


    def osm_research(self, locs : list, printtree=True, union=True, index=0):
        if locs is None:
            return None
            
        local_dlocs = {}
        local_dlocs = self.recursive_research(locs, local_dlocs)
        lroot = self.build_tree(local_dlocs)
        if printtree:
            for root in lroot:
                print_tree(root, style='rounded')

        leaves_ = []
        for root in lroot:
            leaves_.extend(list(root.leaves))

        leaves = [self.recursive_parent(node) for node in leaves_]
        #TO DO -> check if the country of the leaf was in the location, if not the leaf is rejected 
        leaves = set([leaf for leaf in leaves if leaf is not None])

        
        gdf = None
        if len(leaves)>0:
            attr = []
            for leaf in leaves:
                loc = self.dleaf_loc[leaf.node_name]
                loc = self.dlocs[loc]
                attr.append([leaf.node_name, leaf.root.node_name, loc.geometry, loc.area, index])
            attr = np.array(attr)

            if union:
                data = [[",".join(attr.T[0]), ",".join(attr.T[1]), unary_union(attr.T[2]), attr.T[3].sum(), index]]
            else:
                data = attr

            gdf = gpd.GeoDataFrame(data, columns=['name', 'root', 'geometry', 'area_km', 'join_index'], geometry='geometry', \
                crs='epsg:4326')

        return gdf 


    def build_tree(self, local_dlocs : dict) -> list:
        llocs = [locs.displayName for locs in set(list(local_dlocs.values())) if locs.displayName is not None]
        dtree = defaultdict(list)
        for locs in llocs:
            ltree = [node_name.strip() for node_name in locs.replace('/', '-').split(',')[::-1]]
            dtree[ltree[0]].append("/".join(ltree))

        return [list_to_tree(ltree, duplicate_name_allowed=True) for ltree in dtree.values()] 

    def recursive_research(self, locs : list, local_dlocs: dict, count=0, wkt_=True) -> None:

        for loc in locs:
            spatial_entity = self.dlocs.setdefault(loc, defaultvalue(loc, wkt_=wkt_))

            if spatial_entity.displayName is None and count < 1:
                sub_locs = str(loc).split(' ')
                slocs = [" ".join(sub_locs[i:]) for i in range(len(sub_locs))]
                local_dlocs = self.recursive_research(slocs, local_dlocs, count=count+1, wkt_=wkt_)

            #save local dict if wkt are not donwloaded or if above area threshold 
            elif spatial_entity.displayName is not None:
                leaf = spatial_entity.displayName.split(',')[0].replace('/', '-')
                self.dleaf_loc[leaf] = spatial_entity.loc 
                local_dlocs[loc] = self.dlocs[loc]     

        return local_dlocs

    def recursive_parent(self, leaf, displayName=None, count=0):
        
        leaf_name = leaf.node_name
        if count>0:
            default_leaf_name = ",".join(displayName.split(',')[1:])
        else:
            default_leaf_name = leaf_name
        
        loc = self.dleaf_loc.setdefault(leaf_name, default_leaf_name)

        #updatedict
        loc = self.dlocs.setdefault(loc, defaultvalue(loc, wkt_=True))

        if safe_ge(loc.area, self.area_threshold_low) and safe_le(loc.area, self.area_threshold_high):
            return leaf

        elif count < 10 and not leaf.is_root:
            return self.recursive_parent(leaf.parent, loc.displayName, count= count+1)
        else : 
            return None

    

