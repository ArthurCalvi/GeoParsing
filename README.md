# GeoParsing
GeoParser for DataFrame to retrieve the smallest spatial entity. Retrieve the location and create a geometry column. 

## Installation 
Dependencies : 

    pip install -r requirements.txt

NLP model :

    python -m spacy download xx_ent_wiki_sm

## Mechanisms to extract locations 
This algorithm combines NLP and Tree representation to extract the smallest spatial entity of a text. Additionaly, you can set a minimum and maximum value for the surface area retrieved. 

![schema](/images/schema.png)

1. **Extracting interesting words with NLP** : The entity recognition feature of spaCy multi-language model is used to extract locations. ![er](/images/er.png)
2. **Finding matches with OpenStreetMap (or GoogleMaps [optional])** :  an API is used to query the database. Then the results are organized into a tree structure to retrieve the smallest spatial entity. The tree is organised according to administrative relations. ![tree](/images/tree.png)
3. **Extract the geometry : ** The algorithm climb the tree to collect the spatial entity that satisfies some rules on the surface area. For instance, imposing a spatial entity between 100 and 1000 km2 returns the Los Angeles City spatial entity. ![im](/images/ex.png)

## How it works

To start, initialize the OSMGeoParser class with the minimum and maximum surface area thresholds in km2. If you have a GoogleMap API, provide it. Otherwise, OpenStreetMap will be used (results may be less accurate).

```Python
    from  geoparsing  import  OSMGeoParser
    geoparser = OSMGeoParser(area_threshold_low=10, area_threshold_high=90000, googlemapsAPIkey=None)
```

Then load your dataframe and use the `from_dataframe` method. Select the columns that contain textual information. 

```Python
gdf = geoparser.from_dataframe(df, columns=['notes', 'location'])
```

If you have a column that specifies the country you can add it with the `root_in` arg. This will ensure that the spatial entity retrieved is in the country specified in the column. 

```Python
gdf = geoparser.from_dataframe(df, columns=['notes', 'location'], root_in='country')
```

Finally you can bypass the NLP model for extracting locations for some columns using the `enforce` arg.  

```Python
gdf = geoparser.from_dataframe(df, columns=['notes'], root_in='country', enforce=['location'])
```
--- 
Look at example.ipynb 
