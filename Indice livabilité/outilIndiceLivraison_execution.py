#---------------------------------------------------------
#--------------------------------------------------------

# Version 1.0
# Dernière mise à jour : 05.06.2023

# Script de calcul de l'indice de performance du réseau pour le transport urbain de marchandises.
# Ce code est la partie "execution" de l'outil IndiceLivrabilite de ArcGIS Pro

# Code crée dans le cadre du projet de Master en entreprise, réalisé chez Citec, pour l'obtention du titre d'ingénieur EPFL.

# Auteur : Niels Balimann
# Supervision Citec : Franco Tufo & Frédéric Schettini 
# Supervision EPFL : Nikolaos Geroliminis

#-------- Docs et references : --------

#Fonctions os.path pour la gestion des chemin d'accès :
#https://docs.python.org/3/library/os.path.html#module-os.path

#Formatage des string (lettre f et r avant guillemets) : 
#https://docs.python.org/3/reference/lexical_analysis.html#f-strings

#Cursor de arcpy:
#https://pro.arcgis.com/en/pro-app/latest/arcpy/classes/cursor.htm

# API HERE map attribute
# https://developer.here.com/documentation/content-map-attributes/api-reference.html

#---------------------------------------------------------
#--------------------------------------------------------


import arcpy, requests, math, datetime, pandas, json
from sys import argv



# liste des noms de champs des notes d'indicateurs, simplifie le calcul des moyennes ensuite
liste_note_circulation = []
liste_note_accessibilite = []

def unique_values(table , field):
    with arcpy.da.SearchCursor(table, [field]) as cursor:
        return sorted({str(row[0]) for row in cursor})

def seuilStringToList(parametre_seuil):
    parameter_list = parametre_seuil.split(";",1) #permet d'enlever les cas ou l'utilisateur aurait entré plus de lignes dans la table des seuils => Ex output pour 2 lignes de 4 colonnes : "a b c d;e f g h"
    seuil_string = parameter_list[0] #seul la première ligne est gardée (celle remplie par défaut)
    seuil_list = seuil_string.split()
    return seuil_list


   
#-------------- Critere Voie de Circulation -----------------
def calcCritereVoie(Streets_network, seuils):  

    field_name = "Note_NbVoie"
    liste_note_circulation.append(field_name)
    seuils = seuilStringToList(seuils)

    Calculator_Expression = """
def calcCritereLane(field_to_lane,field_from_lane,field_lane_cat,field_dir_travel, field_phys_lane, seuil_bon, seuil_mauv):
    field_lane_cat = int(field_lane_cat)
    if field_phys_lane>=seuil_bon or field_from_lane+field_to_lane>=seuil_bon or field_lane_cat > seuil_bon or (field_lane_cat >= seuil_bon and field_dir_travel == 'B'):
        return 3
    elif field_phys_lane > seuil_mauv or field_from_lane+field_to_lane > seuil_mauv or (field_lane_cat > seuil_mauv and field_dir_travel in ['T','F']) or (field_lane_cat >= seuil_mauv and field_dir_travel == 'B'):
        return 2
    elif field_from_lane+field_to_lane<=seuil_mauv or field_lane_cat < seuil_mauv or (field_lane_cat <= seuil_mauv and field_dir_travel in ['T','F']): 
        return 1
    else :
        return 0
"""
    expression = "calcCritereLane(!FROM_LANES!,!TO_LANES!,!LANE_CAT!,!DIR_TRAVEL!,!PHYS_LANES!,"+seuils[0]+","+seuils[1]+")"

    arcpy.AddMessage("Calcul champ : {} avec seuils {}".format(field_name, seuils))
    
    arcpy.management.CalculateField(in_table=Streets_network, field=field_name, expression=expression, code_block=Calculator_Expression, field_type="SHORT")

    
def calcCritereVoieVelo(Streets_network, table_lane) :

    param_field_name = "BANDE_CYC"
    field_name = "Note_NbVoie"
    liste_note_circulation.append(field_name)



    #Création de la liste des liens ayant une piste cyclable
    Streets_join_Lane = fr"{arcpy.env.scratchGDB}\TEMP_Streets_join_Lane"
    
    # LANE_TYPE = 65536 : bande cyclable
    # Voir manuel Here Navstreet
     
    table_lane, count = arcpy.management.SelectLayerByAttribute(in_layer_or_view=table_lane, where_clause="LANE_TYP = 65536" ) 
    
    arcpy.management.CopyFeatures(in_features=Streets_network, out_feature_class=Streets_join_Lane)
    arcpy.management.JoinField(in_data=Streets_join_Lane, in_field="LINK_ID", join_table=table_lane, join_field="LINK_ID")
    # arcpy.gapro.JoinFeatures(target_layer=Streets_network, join_layer=table_lane, output=Streets_join_Lane, join_operation="JOIN_ONE_TO_MANY", attribute_relationship=[["LINK_ID", "LINK_ID"]], join_condition=join_condition)
    # JoinFeatures fait du toolbox GeoAnalytics Server qui requiert une license

    Streets_join_Lane, count = arcpy.management.SelectLayerByAttribute(in_layer_or_view=Streets_join_Lane, where_clause="LANE_TYP = 65536" ) 
    join_liste_link_id = unique_values(Streets_join_Lane,"LINK_ID")

    
    arcpy.AddMessage("Calcul champ : {} et {}".format(param_field_name,field_name))
    
    #Ajout des champs si pas existants
    if param_field_name not in [f.name for f in arcpy.ListFields(Streets_network)]:
        arcpy.management.AddField(Streets_network, param_field_name, "String")
    if field_name not in [f.name for f in arcpy.ListFields(Streets_network)]:
        arcpy.management.AddField(Streets_network, field_name, "LONG")

    #Mise à jour des champs de la couche
    with arcpy.da.UpdateCursor(Streets_network, ["LINK_ID","LANE_CAT",param_field_name,field_name]) as cursor:
        for row in cursor :
            link = str(row[0])
            lane_cat = int(row[1])
            if link in join_liste_link_id :
                row[2] = "Oui"
            else :
                row[2] = "Non"
            
            if lane_cat <= 1 :
                row[3] = 3
            elif link in join_liste_link_id :
                row[3] = 2
            else :
                row[3] = 1
            
            cursor.updateRow(row)
    
    arcpy.management.Delete(fr"{arcpy.env.scratchGDB}\TEMP_Streets_join_Lane")

#-------------- Critere Vitesse -----------------
def calcCritereVitesse(Streets_network,seuils):  

    field_name = "Note_Vitesse"
    liste_note_circulation.append(field_name)

    seuils = seuilStringToList(seuils)

    Calculator_Expression = """
def calcCritereVitesse(field_to_speed, field_from_speed, seuil_bon, seuil_mauv):
    if (field_to_speed != 0 and field_to_speed <= seuil_mauv) or (field_from_speed != 0 and field_from_speed <= seuil_mauv) or (field_from_speed<=seuil_mauv and field_to_speed<=seuil_mauv):
        return 1
    elif (field_to_speed != 0 and field_to_speed < seuil_bon) or (field_from_speed != 0 and field_from_speed < seuil_bon) or (field_from_speed < seuil_bon and field_to_speed < seuil_bon): 
        return 2
    elif (field_to_speed >= seuil_bon) or (field_from_speed >= seuil_bon) or (field_from_speed >= seuil_bon and field_to_speed >= seuil_bon):
        return 3
    else :
        return 0
"""
    expression = "calcCritereVitesse(!TO_SPD_LIM!, !FR_SPD_LIM!,"+seuils[0]+","+seuils[1]+")"
    
    arcpy.AddMessage("Calcul champ : {} avec seuils {}".format(field_name, seuils))
    
    arcpy.management.CalculateField(in_table=Streets_network, field=field_name, expression=expression, code_block=Calculator_Expression, field_type="SHORT")



#-------------- Retourne les TileID en fonction de l'étendue -----------------
# Calul propre à Here
# Voir : https://developer.here.com/documentation/content-map-attributes/dev_guide/topics/here-map-content.html

def getTileID(lat, long, level):
    tile_size = 180 / math.pow(2,level)
    tileY = math.floor((lat  +  90) / tile_size)
    tileX = math.floor((long + 180) / tile_size)
    tile_id = math.floor(tileY * 2 * math.pow(2, level) + tileX)
    return tile_id

#-------------- Critere Pente -----------------
def calcCriterePente(Streets_network, seuils):
       
    
    param_field_name = "PENTE_MAX"
    field_name = "Note_Pente"
    liste_note_accessibilite.append(field_name)

    seuils = seuilStringToList(seuils)
    
    #Création d'une liste d'identifiants de tuile (tileID) et d'une liste de couche

    # Etendue de la zone étudiée 
    xmin = describe.extent.XMin
    xmax = describe.extent.XMax
    ymin = describe.extent.YMin
    ymax = describe.extent.YMax

    tileID_list = []
    layer_list = []
    batch_size = 64
    merge_data = {"Tiles" :[]}

    # Pour chaque niveau (level), création d'un quadrillage de point 
    # Itération sur les point pour d'obtenir l'identifiant des tuiles sur lesquelles ils sont (avec getTileID)
    # Ajout de la couche d'attribut qui sera appelé en requête (ex : ADAS_ATTRIBUT_FC2 = Attribut ADAS pour les routes de classes 2)
    for level in range(10,14):
        tile_size = 180 / math.pow(2,level)
        lat = ymin
        while lat <= ymax+tile_size:
            long = xmin
            while long <= xmax+tile_size:
                tileID_list.append(getTileID(lat,long,level))
                long += tile_size
                layer_list.append("ADAS_ATTRIB_FC"+str(level-8))
            lat += tile_size
    
    # Préparation du paramètre au format de la requête : "tile:AAAA,BBBB,CCCC,..."
    for batch in range(0, len(layer_list), batch_size) :
        layer_batch = layer_list[batch: batch + batch_size]
        tileID_batch = tileID_list[batch: batch + batch_size]

        in_string = "tile:"

        for tile in tileID_batch:

            in_string = in_string+str(tile)+","

        in_string=in_string[:-1]

        url_tile = "https://smap.hereapi.com/v8/maps/attributes"

        data = requests.get(url_tile, params={
            "layers" : layer_batch,
            "in" : in_string,
            "apiKey": apiKey
        })

        data_json = data.json()
        data_dict = json.loads(data.text)
        merge_data.get("Tiles").extend(data_dict.get("Tiles"))
        merge_json = json.dumps(merge_data, indent=4)
        

    slope_data_dict={}
    
    arcpy.AddMessage("Calcul champ : {} et {} avec seuils {}".format(param_field_name, field_name, seuils))
    
    # Transformation du résultat de la requête en dictionnaire 
    # {link_id : 
    #   {"PENTE_MAX" : max_slope,
    #    "Note_Pente" : note_slope}}
    # 
    # La requête retourne une liste de valeurs de pente en degré pour chaque LINK. Seul la valeur max est gardées et est transformées en pourcent
    # Une note est attribuée en fonction de la pente max 
    for tile in merge_data.get("Tiles"):
        for row in tile.get("Rows"):
            slope_list_str = row.get("SLOPES").split(",")
            max_slope_deg = 0
            for slope_str in slope_list_str :
                slope_deg = abs(int(slope_str)/1000)
                if slope_deg > max_slope_deg:
                    max_slope_deg = slope_deg
                
            max_slope = math.tan(math.radians(max_slope_deg))*100

            note_slope = 0
            if max_slope <= float(seuils[0]) :
                note_slope = 3
            elif max_slope < float(seuils[1]) :
                note_slope = 2
            elif max_slope >= float(seuils[1]) :
                note_slope = 1
            else:
                note_slope = 0

            dict_i = {
                param_field_name : max_slope,
                field_name : note_slope
            }
            slope_data_dict[int(row.get("LINK_ID"))] = dict_i
    

    #Ajout des champs si pas existants
    if param_field_name not in [f.name for f in arcpy.ListFields(Streets_network)]:
        arcpy.management.AddField(Streets_network, param_field_name, "DOUBLE")
    if field_name not in [f.name for f in arcpy.ListFields(Streets_network)]:
        arcpy.management.AddField(Streets_network, field_name, "LONG")

    #Mise à jour des champs de la couche
    with arcpy.da.UpdateCursor(Streets_network, ["LINK_ID",param_field_name,field_name]) as cursor:
        for row in cursor :
            if row[0] in slope_data_dict.keys() :
                row[1] = slope_data_dict[row[0]][param_field_name]
                row[2] = slope_data_dict[row[0]][field_name]
            else :
                row[1] = 0
                row[2] = 3
            cursor.updateRow(row)

def calcNoteGabarit(field_mod_val, seuil_bon, seuil_mauv):
    # Evalue la valeur du modifiers en fonction de seuils et retourne la note
    field_mod_val = int(field_mod_val)
    if field_mod_val >= int(seuil_bon) :
        return 3
    elif field_mod_val > int(seuil_mauv) :
        return 2
    elif field_mod_val <= int(seuil_mauv) :
        return 1
    else : 
        return 3
        
#-------------- Critere Gabarit ----------------- #
def calcCritereGabarit(Streets_network, Streets_join_CdmsMod, seuils):

    param_field_name_list = ["LIM_HAUT", "LIM_POIDS", "LIM_ChESSIEU","LIM_LONG","LIM_LARG"]
    field_name = "Note_Gabarit"
    liste_note_accessibilite.append(field_name)

    seuils = seuilStringToList(seuils)
    arcpy.AddMessage("Calcul champ : {} et {} avec seuils {}".format(param_field_name_list,field_name, seuils))

    # COND_TYPE = 23 : Transport Access Restriction
    # MOD_TYPE = 41 : Height Restriction
    # MOD_TYPE = 42 : Weight Restriction
    # MOD_TYPE = 43 : Weight per Axle
    # MOD_TYPE = 44 : Length Restriction
    # MOD_TYPE = 45 : Width Restriction
    # Voir manuel Here Navstreet
    where_clause = "COND_TYPE = 23 AND (MOD_TYPE = 41 OR MOD_TYPE = 42 OR MOD_TYPE = 43 OR MOD_TYPE = 44 OR MOD_TYPE = 45)"

    gabarit_dict = dict()
    
    #Itération sur les LINK et mise à jour du dictionnaire des restrictions
    with arcpy.da.SearchCursor(Streets_join_CdmsMod, ["LINK_ID","COND_TYPE","MOD_TYPE", "MOD_VAL"], where_clause=where_clause) as cursor :

        for row in cursor :
            link_id = str(row[0])
            
            if link_id not in liste_link_id:
                continue
            
            if link_id not in gabarit_dict.keys():
                gabarit_dict[link_id]={"note" : [3,3,3,3,3]}
            if row[2] == 41:
                gabarit_dict[link_id][param_field_name_list[0]] = str(row[3])
                gabarit_dict[link_id]["note"][0] = calcNoteGabarit(row[3], seuils[0], seuils[1])
            else :
                gabarit_dict[link_id][param_field_name_list[0]] = "Aucun"
            if row[2] == 42:
                gabarit_dict[link_id][param_field_name_list[1]] = str(row[3])
                gabarit_dict[link_id]["note"][1] = calcNoteGabarit(row[3], seuils[2],seuils[3])
            else :
                gabarit_dict[link_id][param_field_name_list[1]] = "Aucun"
            if row[2] == 43:
                gabarit_dict[link_id][param_field_name_list[2]] = str(row[3])
                gabarit_dict[link_id]["note"][2] = calcNoteGabarit(row[3], seuils[4],seuils[5])
            else :
                gabarit_dict[link_id][param_field_name_list[2]] = "Aucun"
            if row[2] == 44:
                gabarit_dict[link_id][param_field_name_list[3]] = str(row[3])
                gabarit_dict[link_id]["note"][3] = calcNoteGabarit(row[3], seuils[6],seuils[7])
            else :
                gabarit_dict[link_id][param_field_name_list[3]] = "Aucun"
            if row[2] == 45:
                gabarit_dict[link_id][param_field_name_list[4]] = str(row[3])
                gabarit_dict[link_id]["note"][4] = calcNoteGabarit(row[3], seuils[8],seuils[9])
            else :
                gabarit_dict[link_id][param_field_name_list[4]] = "Aucun"
            

    for link in gabarit_dict:
        gabarit_dict[link][field_name] = min(gabarit_dict[link]["note"])

    
    #Ajout des champs si pas existants
    for param_field_name in param_field_name_list :
        if param_field_name not in [f.name for f in arcpy.ListFields(Streets_network)]:
            arcpy.management.AddField(Streets_network, param_field_name, "STRING")
        
    if field_name not in [f.name for f in arcpy.ListFields(Streets_network)]:
        arcpy.management.AddField(Streets_network, field_name, "LONG")

   #Mise à jour des champs de la couche
    with arcpy.da.UpdateCursor(Streets_network, ["LINK_ID"]+param_field_name_list+[field_name]) as cursor:
        for row in cursor:
            link_id = str(row[0])
            if link_id in gabarit_dict.keys():
                for i in range(1,6):
                    row[i] = gabarit_dict[link_id][param_field_name_list[i-1]]
                row[6] = gabarit_dict[link_id][field_name]
            else :
                for i in range(1,6):
                    row[i] = "Aucun"
                row[6] = 3
            cursor.updateRow(row)

#-------------- Critere Obstacle -----------------
def calcCritereObstacle(Streets_network, Streets_join_CdmsMod, seuils):

    # COND_TYPE = 10 : Special Speed Situation et COND_VAL1 = SPEED BUMPS PRESENT' : Special Speed Type = Speed Bumps Present
    # COND_TYPE = 17 : Traffic Sign et MOD_VAL='41' : Pedestrian Crossing
    # COND_TYPE = 18 : Railway Crossing
    # Voir manuel Here Navstreet
    where_clause = "(COND_TYPE=10 AND COND_VAL1='SPEED BUMPS PRESENT') OR (COND_TYPE=17 AND MOD_VAL='41') OR COND_TYPE=18"
    
    param_field_name = "NB_OBSTACLE"
    field_name = "Note_Obstacle"
    liste_note_circulation.append(field_name)

    seuils = seuilStringToList(seuils)
    arcpy.AddMessage("Calcul champ : {} et {} avec seuils {}".format(param_field_name, field_name, seuils))

    # Compte du nombre d'obstacle par link et évaluation de la note
    # Assignation dans un dictionnaire
    # {link_id : 
    #   {"NB_OBSTACLE" : compte,
    #    "Note_Obstacle" : note}}
    obs_dict = dict()
    with arcpy.da.SearchCursor(Streets_join_CdmsMod, ["LINK_ID","COND_TYPE", "MOD_VAL"], where_clause=where_clause) as cursor :
        for row in cursor :
            link_id = str(row[0])
            if link_id in obs_dict.keys():
                obs_dict[link_id][param_field_name] += 1
            else :
                obs_dict[link_id] = {param_field_name: 1}
    for link in obs_dict.keys():
        compte = obs_dict[link][param_field_name]
        if (compte <= int(seuils[0])):
            obs_dict[link][field_name] = 3
        elif (compte < int(seuils[1])):
            obs_dict[link][field_name] = 2
        elif (compte >= int(seuils[1])):
            obs_dict[link][field_name] = 1
        else:
            obs_dict[link][field_name] = 0
    
    #Ajout des champs si pas existants
    if param_field_name not in [f.name for f in arcpy.ListFields(Streets_network)]:
        arcpy.management.AddField(Streets_network, param_field_name, "LONG")
    if field_name not in [f.name for f in arcpy.ListFields(Streets_network)]:
        arcpy.management.AddField(Streets_network, field_name, "LONG")

    #Mise à jour des champs de la couche
    with arcpy.da.UpdateCursor(Streets_network, ["LINK_ID",param_field_name,field_name]) as cursor:
        for row in cursor :
            link_str = str(row[0])
            if link_str in obs_dict.keys() :
                row[1] = obs_dict[link_str][param_field_name]
                row[2] = obs_dict[link_str][field_name]
            else :
                row[1] = 0
                row[2] = 3
            cursor.updateRow(row)

#-------------- Critere Carrefour -----------------
def calcCritereCarrefour(Streets_network, Streets_join_CdmsMod): 

    # COND_TYPE = 16 : Traffic Signal
    # COND_TYPE = 17 : Traffic Sign et MOD_TYPE = 22 : Traffic Sign Type
    # MOD_VAL = '20' : Stop Sign
    # MOD_VAL = '37' : Crossing with priority to the right
    # MOD_VAL = '42' : Yield
    # Voir manuel Here Navstreet
    where_clause = "COND_TYPE = 16 OR ((COND_TYPE = 17 AND MOD_TYPE = 22) AND (MOD_VAL = '20' OR MOD_VAL = '37' OR MOD_VAL = '42'))"
    
    param_field_name = "TYPE_CARR"
    field_name = "Note_Carrefour"
    liste_note_circulation.append(field_name)

    arcpy.AddMessage("Calcul champ : {} et {}".format(param_field_name, field_name))
    
    # Lecture du type et assignation dans un dictionnaire en valeur nominale, avec la note.
    carr_dict = dict()
    with arcpy.da.SearchCursor(Streets_join_CdmsMod, ["LINK_ID","COND_TYPE", "MOD_TYPE", "MOD_VAL"], where_clause=where_clause) as cursor :
        for row in cursor :
            link_id = row[0]
            cond_type = row[1]
            mod_type = row[2]
            mod_val = row[3]
            if cond_type == 16:
                carr_dict[link_id] = {param_field_name : "Feux", field_name : 2}
            elif cond_type == 17 and mod_type == 22:
                mod_val = int(mod_val)
                if mod_val == 20 :
                    carr_dict[link_id] = {param_field_name : "Stop", field_name : 1}
                elif mod_val == 37 :
                    carr_dict[link_id] = {param_field_name : "Priorité droite", field_name : 2}
                elif mod_val == 42:
                    carr_dict[link_id] = {param_field_name : "Cédez passage", field_name : 2}
                else :
                    carr_dict[link_id] = {param_field_name : "Prioritaire", field_name : 3}
            else :
                carr_dict[link_id] = {param_field_name : "Prioritaire", field_name : 3}

    #Ajout des champs si pas existants
    if param_field_name not in [f.name for f in arcpy.ListFields(Streets_network)]:
        arcpy.management.AddField(Streets_network, param_field_name, "STRING")
    if field_name not in [f.name for f in arcpy.ListFields(Streets_network)]:
        arcpy.management.AddField(Streets_network, field_name, "LONG")

    #Mise à jour des champs de la couche
    with arcpy.da.UpdateCursor(Streets_network, ["LINK_ID","ROUNDABOUT",param_field_name,field_name]) as cursor:
        for row in cursor :
            if row[0] in carr_dict.keys() :
                row[2] = carr_dict[row[0]][param_field_name]
                row[3] = carr_dict[row[0]][field_name]
            elif row[1] == 'Y' :
                row[2] = "Giratoire"
                row[3] = 2
            else :
                row[2] = "Prioritaire"
                row[3] = 3
            cursor.updateRow(row)

def dureeAccesSemaine(DTTME_TYPE, REF_DATE, STARTTIME, ENDTIME, AR_AUTO, AR_TRUCKS, AR_DELIVER):
    # Calcul du nombre d'heure autorisées (valeur positive) ou interdites (valeur négative) à la circulation des véhicule de livraison par semaine
    
    # Formatage des données d'heure de début/fin pour utiliser le module datetime
    # 24:00 n'est pas reconnu par datetime donc transformatin en 00:00 et ajout d'une valeur "add_reverse" pour compenser l'inversion du calcul
    #  Ex : 18:00 -> 24:00 => 6 (heure)
    # Mais 18:00 -> 00:00 => -18 (heure)
    # Donc ajout de +24 (heure) pour compenser

    # REF_DATE : Suite de 7 Y/N pour signifier si la restriction s'applique ou non durant les jours de la semaines (commence par dimanche)
    # Ex : restriction tous les jours sauf samedi et dimanche => "NYYYYYN"
    # voir manuel Here Navstreet

    # AR_AUTO et AR_DELIVER ne sont pas utilsé dans cette fonction. 
    # La modélisation de l'accessibilité d'une route par HERE est décrite de manière floue dans le manuel.
    # Il serait possible afinner l'analyse par tronçon en considérant ces deux champs 
    
    if DTTME_TYPE != '1' : # Daymask, voir manuel Here Navstreet
        return 0
    if ENDTIME == "2400" :
        ENDTIME = "0000"
        add_reverse = 24
    else:
        add_reverse = 0
    STARTTIME = STARTTIME[:-2]+":"+STARTTIME[-2:]
    ENDTIME = ENDTIME[:-2]+":"+ENDTIME[-2:]
    STARTTIME = datetime.datetime.strptime(STARTTIME,"%H:%M")
    ENDTIME = datetime.datetime.strptime(ENDTIME,"%H:%M")
    delta = (ENDTIME-STARTTIME)
    day_count = REF_DATE.count("Y")
    hrs = day_count*(add_reverse+(delta.total_seconds()/3600))
    if AR_TRUCKS == 'N': 
        return(-1*hrs)
    else:
        return hrs

#-------------- Critere Horaire ----------------- 
def calcCritereHoraire(Streets_network, Streets_join_CdmsDTMod, seuils):
    # Amélioration possible : 
    #   - ENLEVER DIMANCHE dans le calcul
    #   - Paramètres de l'utilsateur pour choisir les jours

    param_field_name = "ACCES_PJOUR"
    field_name = "Note_Horaire"
    liste_note_accessibilite.append(field_name)

    seuils = seuilStringToList(seuils)
    arcpy.AddMessage("Calcul champ : {} et {} avec seuils {}".format(param_field_name, field_name, seuils))
    hor_dict = dict()
    # Compte du nombre d'heure moyen par jour par link et évaluation de la note
    # Assignation dans un dictionnaire
    # {link_id : 
    #   {   "total" : hrs total par semaine,
    #       "ACCES_PJOUR" : hrs moyen par jour,
    #       "Note_Horaire" : note}}

    with arcpy.da.SearchCursor(Streets_join_CdmsDTMod, ["LINK_ID","DTTME_TYPE","REF_DATE","STARTTIME","ENDTIME", "AR_AUTO","AR_TRUCKS", "AR_DELIVER"], where_clause=" AR_DELIVER <> 'N' ") as cursor :
        # where_clause : les link qui ne sont pas accessible aux livraisons ne sont pas pris en compte.
        for row in cursor :
            LINK_ID, DTTME_TYPE, REF_DATE, STARTTIME, ENDTIME, AR_AUTO, AR_TRUCKS, AR_DELIVER = [str(e) for e in row]
        
            hrs = dureeAccesSemaine(DTTME_TYPE, REF_DATE, STARTTIME, ENDTIME, AR_AUTO, AR_TRUCKS, AR_DELIVER)
            if LINK_ID in hor_dict.keys():
                hor_dict[LINK_ID]["total"] += hrs
            else :
                hor_dict[LINK_ID] = {"total" : hrs}
        for link in hor_dict.keys():
            total = hor_dict[link]["total"]
            # si négatif : nombre d'heure où l'accès est interdit aux véhicules de livraison
            # sinon nombre d'heure où l'accès est autorisé

            # Moyenne/jour
            if total < 0 : 
                param_field_val = (total/7)+24
            else :
                param_field_val = total/7

            # Note
            if param_field_val>=int(seuils[0]) :
                note_horaire = 3
            elif param_field_val>int(seuils[1]):
                note_horaire = 2
            elif param_field_val<=int(seuils[1]):
                note_horaire = 1
            else:
                note_horaire = 0
            
            #Assignation dictionnaire
            hor_dict[link] = {param_field_name : param_field_val, field_name : note_horaire}

    #Ajout des champs si pas existants
    if param_field_name not in [f.name for f in arcpy.ListFields(Streets_network)]:
        arcpy.management.AddField(Streets_network, param_field_name, "DOUBLE")
    if field_name not in [f.name for f in arcpy.ListFields(Streets_network)]:
        arcpy.management.AddField(Streets_network, field_name, "LONG")

    #Mise à jour des champs de la couche
    with arcpy.da.UpdateCursor(Streets_network, ["LINK_ID",param_field_name,field_name]) as cursor:
        for row in cursor :
            link = str(row[0])
            if link in hor_dict.keys() :
                row[1] = hor_dict[link][param_field_name]
                row[2] = hor_dict[link][field_name]
            else :
                row[1] = 24
                row[2] = 3
            cursor.updateRow(row)
    


#-------------- Critere Stationnement -----------------
def calcCritereStationnement(Streets_network, couche_stationnement, filtre_stat, champ_nb_place, distance, nb_defaut, seuils):

    
    param_field_name = "NB_PLACE"
    field_name = "Note_Stationnement"
    liste_note_accessibilite.append(field_name)

    seuils = seuilStringToList(seuils)
    arcpy.AddMessage("Calcul champ : {} et {} avec\n filtre : {}\n champ nb place : {}\n distance : {}\n nb defaut : {}\n seuils {}".format(param_field_name, field_name, filtre_stat,champ_nb_place, distance, nb_defaut, seuils))

    
    Code_Block = """
def calcCritereStationnement(nb_place, borne_bon, borne_mauv):
    if (nb_place >= borne_bon):
        return 3
    elif (nb_place > borne_mauv):
        return 2
    elif (nb_place <= borne_mauv):
        return 1
    else:
        return 0
    """

    # Le script renvoie la valeur '#' dans python si le paramètres est laissé vide par l'utilisateur
    if filtre_stat == "#":
        filtre_stat = ""
    
    couche_stationnement, count = arcpy.management.SelectLayerByAttribute(in_layer_or_view=couche_stationnement, where_clause=filtre_stat)
    
    Streets_SummarizeNearby = fr"{arcpy.env.scratchGDB}\TEMP_Streets_SummarizeNearby"
    arcpy.analysis.SummarizeNearby(in_features=Streets_network, in_sum_features=couche_stationnement, out_feature_class=Streets_SummarizeNearby, distance_type="STRAIGHT_LINE", distances=distance, distance_units="METERS", sum_fields=[[champ_nb_place, "Sum"]])
    
    sum_field = arcpy.AddFieldDelimiters(Streets_network,"sum_"+champ_nb_place) #"sum_NomDuChamp" est un champ créé automatiquement par SummarizeNearby
    if sum_field not in [f.name for f in arcpy.ListFields(Streets_network)]: #Ajouté à la couche réseau si n'exsite pas déjà
        arcpy.management.JoinField(in_data=Streets_network, in_field="LINK_ID", join_table=Streets_SummarizeNearby, join_field="LINK_ID", fields=[sum_field])

    arcpy.management.CalculateField(in_table=Streets_network, field=sum_field, expression=f"math.ceil(!{sum_field}!)+{nb_defaut}") #Arrondi du champ de somme à l'entier supérieur
    arcpy.management.CalculateField(in_table=Streets_network, field=field_name, expression=f"calcCritereStationnement(!{sum_field}!, {seuils[0]}, {seuils[1]})", code_block=Code_Block, field_type="SHORT")

    arcpy.management.Delete(fr"{arcpy.env.scratchGDB}\TEMP_Streets_SummarizeNearby")

#-------------- Critere Congestion -----------------
def calcNoteCongestion(R_i_T, R_i_F, seuil_bon, seuil_mauv):
    # R_i_T Indice Ri (Road segment congestion index) pour la direction T (=To)
    # R_i_F Indice Ri (Road segment congestion index) pour la direction F (=From)
    if R_i_T ==  0 and R_i_F == 0 :
        return 3
    if R_i_T == 0:
        ratio = R_i_F
    elif R_i_F == 0:
        ratio = R_i_T
    else :
        ratio = min(R_i_T,R_i_F)

    if ratio >= seuil_bon:
        return 3
    elif ratio > seuil_mauv:
        return 2
    elif ratio <= seuil_mauv:
        return 1
    else :
        0

def calcNbNonCongested(row):
    count_non_cong = 0
    for i in range(2,len(row)-1):
        if row[i]< 50:
            continue
        count_non_cong +=1
    return count_non_cong

def calcRoadSegmentCongestionIndex(row):
    return (row["SPI_AVG"]/100)*(row["Nb_CongStat"]/(len(row)-4))

def calcCritereCongestion(Streets_network, table_speed_data, heure_analyse, seuils):
    

    param_field_name_T = "CONG_RSI_T"
    param_field_name_F = "CONG_RSI_F"
    field_name = "Note_Congestion"
    liste_note_circulation.append(field_name)

    seuils = seuilStringToList(seuils)

    arcpy.AddMessage("Lecture .csv et traitement données")
    df = pandas.read_csv(table_speed_data, sep=",")

    # Tri en fonction des heures choisies pour l'analyse
    if heure_analyse :
        heure_liste = [int(e) for e in heure_analyse.split(";")]
        df = df[df['EPOCH-60MIN'].isin(heure_liste)]
    

    # Permet de garder le lien en mémoire et de faire l'itération sur les mesures par lien
    cur_link_id = ""
    cur_link_dict = {}
    
    df_ratio = pandas.DataFrame()

    for index, row in df.iterrows():
        
        link_dir= row["LINK-DIR"]
        # Séparation link id et link dir
        link_id = link_dir[:-1]
        link_dir = link_dir[-1:]
        
        # Comme la requête SpeedData est faite sur une étendue plus grande que la couche réseau, on verifie d'abord si le lien fait partie de la couche ou non
        if link_id not in liste_link_id:
            continue
        
        date_time = row["DATE-TIME"]

        # Calcul Speed Performance Index (SPI)
        ratio = int(100*(float(row["MEAN"])/float(row["FREEFLOW"]))) 
        ratio = ratio if ratio<= 100 else 100
        
        if link_id != cur_link_id : # SI vrai : on a finit d'itérer sur le lien en cours
            
            # Si le dictionnaire n'est pas vide, cela signifie que des valeurs ont été calculées et qu'il faut les ajouter au df des ratios
            # Un DataFrame est créé et appondu au df des ratios.
            if cur_link_dict:
                df_cur = pandas.DataFrame(cur_link_dict, index=[0])
                df_ratio = pandas.concat([df_ratio,df_cur],ignore_index=True)
            cur_link_dict = {}
            cur_link_id = link_id
            cur_link_dict["link_id"] = link_id
            cur_link_dict["link_dir"] = link_dir
        
        cur_link_dict[date_time] = ratio
    
    df_ratio["SPI_AVG"] = df_ratio.iloc[:, df_ratio.columns != "link_id"].mean(axis=1, numeric_only=True)
    df_ratio["Nb_CongStat"] = df_ratio.apply(calcNbNonCongested, axis=1)
    df_ratio["R_i"] = df_ratio.apply(calcRoadSegmentCongestionIndex, axis=1)


    arcpy.AddMessage("Calcul champ : {}, {} et {} avec seuils {}".format(param_field_name_T,param_field_name_F,field_name,seuils))
    #Ajout des champs si pas existants
    if param_field_name_T not in [f.name for f in arcpy.ListFields(Streets_network)]:
        arcpy.management.AddField(Streets_network, param_field_name_T, "DOUBLE")
    if param_field_name_F not in [f.name for f in arcpy.ListFields(Streets_network)]:
        arcpy.management.AddField(Streets_network, param_field_name_F, "DOUBLE")
    if field_name not in [f.name for f in arcpy.ListFields(Streets_network)]:
        arcpy.management.AddField(Streets_network, field_name, "LONG")

    #Mise à jour des champs de la couche
    with arcpy.da.UpdateCursor(Streets_network, ["LINK_ID",param_field_name_T,param_field_name_F,field_name]) as cursor:
        for row in cursor :
            link = str(row[0])
            df_extract_T = df_ratio.loc[(df_ratio['link_id']==link)&(df_ratio["link_dir"]=="T") ,"R_i"]
            df_extract_F = df_ratio.loc[(df_ratio['link_id']==link)&(df_ratio["link_dir"]=="F") ,"R_i"]
            R_i_T = 0 if df_extract_T.empty else df_extract_T.values[0]
            R_i_F = 0 if df_extract_F.empty else df_extract_F.values[0]
            row[1] = R_i_T
            row[2] = R_i_F
            
            row[3] = calcNoteCongestion(R_i_T=R_i_T, R_i_F=R_i_F,seuil_bon=float(seuils[0].replace(",",".")),seuil_mauv=float(seuils[1].replace(",",".")))           
            
            cursor.updateRow(row)
    
#-------------- Critere Chantier -----------------
def convertCritChantier(crit):
    if crit == "critical" :
        return 4
    elif crit == "major" :
        return 3
    elif crit == "minor" :
        return 2
    elif crit == "low" :
        return 1
    else :
        return 0

def calcNoteChantier(crit_int, duree, seuil_bon, seuil_mauv):
    if crit_int == 0:
        if duree <= seuil_bon:
            return 3
        elif duree < seuil_mauv:
            return 2
        elif duree >= seuil_mauv:
            return 1
        else :
            return 0
        
    if (crit_int <= 1 and duree <= seuil_bon) or (crit_int < 3 and duree <= seuil_bon) or (crit_int <= 1 and duree < seuil_mauv) :
        return 3
    elif (crit_int <= 1) or (duree <= seuil_bon) or (crit_int < 3 and duree < seuil_mauv) :
        return 2
    elif crit_int >= 3 or duree >= seuil_mauv:
        return 1
    else :
        return 0

def calcCritereChantierHere(Streets_network, filtre_type, filtre_impact, seuils):
    # doc : 
    # https://developer.here.com/documentation/traffic-api/dev_guide/topics/use-cases/incidents.html
    # https://developer.here.com/documentation/traffic-api/api-reference.html

    impact_chantier_field_name = "IMPACT_CHANTIER"
    debut_chantier_field_name = "DEBUT_CHANTIER"
    fin_chantier_field_name = "FIN_CHANTIER"

    param_field_name = "DUREE_CHANTIER"
    field_name = "Note_Chantier"
    liste_note_circulation.append(field_name)

    seuils = seuilStringToList(seuils)


    desc = arcpy.Describe(Streets_network)
    xmin = desc.extent.XMin
    xmax = desc.extent.XMax
    ymin = desc.extent.YMin
    ymax = desc.extent.YMax

    spa_ref = desc.spatialReference

    bbox = "bbox:{w_lon},{s_lat},{e_lon},{n_lat}".format(w_lon=xmin,s_lat=ymin,e_lon=xmax,n_lat=ymax)
    
    #Si l'utilisateur ne rentre pas de filtre, la valeur retrounée dans l'outil est un string = "#", dans ce cas, tous les types et catégories d'impact sont envoyés dans la requête API
    #Si les filtres sont peuplés (ont des valeurs), c'est un string qui est retournés avec les choix séparés par des ";" ex: "critical;major;minor", ce string est transformé en liste

    if filtre_type == "#":
        filtre_type = ["accident", "construction", "congestion","disabledVehicle","massTransit","plannedEvent","roadHazard","roadClosure","weather","laneRestriction","other"]
    else :
        filtre_type = filtre_type.split(";")
    

    if filtre_impact == "#":
        filtre_impact = ["critical","major","minor","low"]
    else :
        filtre_impact = filtre_impact.split(";")

    # doc : https://developer.here.com/documentation/traffic-api/dev_guide/topics/concepts/incidents.html#incidents
    arcpy.AddMessage("Requete API HERE avec\n filtre impact : {}\n filtre type : {}".format(filtre_impact, filtre_type))
    url_incident = "https://data.traffic.hereapi.com/v7/incidents"
    data = requests.get(url_incident, params={
        "in" : bbox,
        "locationReferencing" : "shape", # 3 valeurs possible : tmc, olr, shape
        "criticality" : ",".join(filtre_impact), # 4 valeurs possible : critical, major, minor, low
        "type" : ",".join(filtre_type), 
        "lang" : "fr-FR", # traduction en français des événements (de-DE par défaut pour la suisse)
        "apiKey": apiKey
        # "earliestStartTime" : Seul les événements EN COURS sont retournés,  si earliestStartTime est après aujourd'hui -> réponse vide
        # "latestEndTime" : si latestEndTime est avant aujourd'hui -> réponse vide
    })
    data_json = data.json()

    incid_list = []

    arcpy.AddMessage("Calcul champ : {}, {}, {}, {}, {} avec seuils {}".format(impact_chantier_field_name, debut_chantier_field_name, fin_chantier_field_name, param_field_name, field_name, seuils))
    for incident in data_json.get("results"):
        links = incident.get("location").get("shape").get("links") #list of links
        
        #Création d'un objet géomètrie (Polyline) d'après la liste de point
        point_list = []
        for link in links :
            points = link.get("points")
            for point in points :
                point_list.append(arcpy.Point(point.get("lng"), point.get("lat")))

        geometry = arcpy.Polyline(arcpy.Array(point_list),spa_ref)
        
        incidentDetails = incident.get("incidentDetails") #dict des détails des incidents
        
        date_debut = datetime.datetime.strptime(incidentDetails.get("startTime"),"%Y-%m-%dT%H:%M:%SZ")
        date_fin = datetime.datetime.strptime(incidentDetails.get("endTime"),"%Y-%m-%dT%H:%M:%SZ")
        
        incid_list.append({
            "geometry" : geometry,
            debut_chantier_field_name : date_debut, 
            fin_chantier_field_name : date_fin,
            param_field_name : (date_fin-date_debut).days, # Durée
            impact_chantier_field_name : incidentDetails.get("criticality")
        })

    #Ajout des champs si pas existants
    if impact_chantier_field_name not in [f.name for f in arcpy.ListFields(Streets_network)]:
        arcpy.management.AddField(Streets_network, impact_chantier_field_name, "String")
    if debut_chantier_field_name not in [f.name for f in arcpy.ListFields(Streets_network)]:
        arcpy.management.AddField(Streets_network, debut_chantier_field_name, "DATE")
    if fin_chantier_field_name not in [f.name for f in arcpy.ListFields(Streets_network)]:
        arcpy.management.AddField(Streets_network, fin_chantier_field_name, "DATE")
    if param_field_name not in [f.name for f in arcpy.ListFields(Streets_network)]:
        arcpy.management.AddField(Streets_network, param_field_name, "LONG")
    if field_name not in [f.name for f in arcpy.ListFields(Streets_network)]:
        arcpy.management.AddField(Streets_network, field_name, "LONG")

    #Mise à jour des champs de la couche
    with arcpy.da.UpdateCursor(Streets_network, ["SHAPE@",impact_chantier_field_name, debut_chantier_field_name, fin_chantier_field_name, param_field_name,field_name]) as cursor :
        for row in cursor :
            shape = row[0]
            note_max = 0
            for incid in incid_list :
                
                if shape.distanceTo(incid.get("geometry"))>0.00001: # valeur en degré (unité du système de référence spatial) = ~1 millimètre
                    continue
                # .distanceTo() permet de couvrir le plus grand nombre de cas possible
                # .intersect() ne prend pas en compte les geometries superposees
                # il peut aussi arriver que les deux geometries soient tres legerement decalees et ne se touchent pas
                # la tres petite valeur permet aussi de limiter au maximum les erreurs aux extrémités des arcs
                
                note = calcNoteChantier(convertCritChantier(incid.get(impact_chantier_field_name)),incid.get(param_field_name),int(seuils[0]), int(seuils[1]))
                if note <= note_max :
                    continue
                
                note_max = note
                row[1] = incid.get(impact_chantier_field_name)
                row[2] = incid.get(debut_chantier_field_name)
                row[3] = incid.get(fin_chantier_field_name)
                row[4] = incid.get(param_field_name)
                row[5] = note
                
        
            
            if note_max == 0 :
                row[1] = "Aucun"
                row[2] = None
                row[3] = None
                row[4] = 0
                row[5] = 3
            
            
            cursor.updateRow(row)

def calcCritereChantierExt(Streets_network, couche_ext_chantier, champ_debut_chantier, champ_fin_chantier, filtre_date_chantier, filtre_valeur_chantier, seuils):
    
    impact_chantier_field_name = "IMPACT_CHANTIER"
    debut_chantier_field_name = "DEBUT_CHANTIER"
    fin_chantier_field_name = "FIN_CHANTIER"

    param_field_name = "DUREE_CHANTIER"
    field_name = "Note_Chantier"
    liste_note_circulation.append(field_name)

    seuils = seuilStringToList(seuils)

    
    #Si l'utilisateur ne rentre pas de filtre, la valeur retrounée dans l'outil est un string = "#", mais renvoie une erreur lorsque assigné a where_clause directement
    if filtre_valeur_chantier == "#":
        filtre_valeur_chantier = ""

    couche_chantier_select_type, count = arcpy.management.SelectLayerByAttribute(in_layer_or_view=couche_ext_chantier, where_clause=filtre_valeur_chantier)

    if filtre_date_chantier == "#":
        filtre_date_chantier = f"{champ_debut_chantier} < CURRENT_DATE And {champ_fin_chantier} > CURRENT_DATE"


    
    couche_chantier_select, count = arcpy.management.SelectLayerByAttribute(in_layer_or_view=couche_chantier_select_type, where_clause=filtre_date_chantier)

    arcpy.AddMessage("Jointure des chantiers de la couche {} avec\n filtre valeur : {}\n filtre date : {}".format(couche_ext_chantier, filtre_valeur_chantier, filtre_date_chantier))
    
    fldmappings = arcpy.FieldMappings()
   
    
    fldmap_link = arcpy.FieldMap()
    fldmap_link.addInputField(Streets_network, "LINK_ID")
    fld_link = fldmap_link.outputField
    fld_link.name = "LINK_ID"
    fldmap_link.outputField = fld_link
    fldmappings.addFieldMap(fldmap_link)

    fldmap_chp_debut = arcpy.FieldMap()
    fldmap_chp_debut.addInputField(couche_chantier_select, champ_debut_chantier)
    fld_chp_debut = fldmap_chp_debut.outputField
    fld_chp_debut.name = debut_chantier_field_name
    fldmap_chp_debut.outputField = fld_chp_debut
    fldmappings.addFieldMap(fldmap_chp_debut)

    fldmap_chp_fin = arcpy.FieldMap()
    fldmap_chp_fin.addInputField(couche_chantier_select, champ_fin_chantier)
    fld_chp_fin = fldmap_chp_fin.outputField
    fld_chp_fin.name = fin_chantier_field_name
    fldmap_chp_fin.outputField = fld_chp_fin
    fldmappings.addFieldMap(fldmap_chp_fin)
    
    Streets_join_chantier = fr"{arcpy.env.scratchGDB}\TEMP_Streets_join_chantier"
    arcpy.analysis.SpatialJoin(target_features=Streets_network, join_features=couche_chantier_select, out_feature_class=Streets_join_chantier, join_operation="JOIN_ONE_TO_MANY", join_type="KEEP_ALL", field_mapping=fldmappings, match_option="INTERSECT")

    chantier_dict = dict()

    with arcpy.da.SearchCursor(Streets_join_chantier,["LINK_ID", debut_chantier_field_name, fin_chantier_field_name]) as cursor:
        for row in cursor:
            link_id = str(row[0])
            date_debut = row[1]
            date_fin = row[2]
            impact = "Pas d'information"

            if date_debut is None or date_fin is None: #Pas possible de calculer la durée
                if link_id in chantier_dict.keys(): #Le link concerné est déjà affecté par un autre chantier, on passe au chantier suivant
                    continue
                else : # On assigne les valeurs du chantier en cours et on passe au suivant
                    chantier_dict[link_id] = {
                        impact_chantier_field_name : impact,
                        debut_chantier_field_name : date_debut,
                        fin_chantier_field_name : date_fin,
                        param_field_name : 0,
                        field_name : 3
                        }
                    continue
            
            duree = date_fin-date_debut
            duree = duree.days

            if link_id not in chantier_dict.keys(): # Le link n'est pas déjà affecté par un autre chantier
                chantier_dict[link_id] = {
                    impact_chantier_field_name : impact,
                    debut_chantier_field_name : date_debut,
                    fin_chantier_field_name : date_fin,
                    param_field_name : duree,
                    field_name : calcNoteChantier(convertCritChantier(impact), duree, int(seuils[0]), int(seuils[1]))
                    }
                continue
            
            if duree <= chantier_dict[link_id][param_field_name]: # Vérifie sir le chantier en cours d'étérations à une durée plus faible que celui déjà enregistré pour le link correspondant
                continue

            chantier_dict[link_id] = {
                impact_chantier_field_name : impact,
                debut_chantier_field_name : date_debut,
                fin_chantier_field_name : date_fin,
                param_field_name : duree,
                field_name : calcNoteChantier(convertCritChantier(impact), duree, int(seuils[0]), int(seuils[1]))
                }

    arcpy.AddMessage("Calcul champ : {}, {}, {}, {}, {} avec seuils {}".format(impact_chantier_field_name, debut_chantier_field_name, fin_chantier_field_name, param_field_name, field_name, seuils))   
    #Ajout des champs si pas existants
    if impact_chantier_field_name not in [f.name for f in arcpy.ListFields(Streets_network)]:
        arcpy.management.AddField(Streets_network, impact_chantier_field_name, "String")
    if debut_chantier_field_name not in [f.name for f in arcpy.ListFields(Streets_network)]:
        arcpy.management.AddField(Streets_network, debut_chantier_field_name, "DATE")
    if fin_chantier_field_name not in [f.name for f in arcpy.ListFields(Streets_network)]:
        arcpy.management.AddField(Streets_network, fin_chantier_field_name, "DATE")
    if param_field_name not in [f.name for f in arcpy.ListFields(Streets_network)]:
        arcpy.management.AddField(Streets_network, param_field_name, "LONG")
    if field_name not in [f.name for f in arcpy.ListFields(Streets_network)]:
        arcpy.management.AddField(Streets_network, field_name, "LONG")

    #Mise à jour des champs de la couche
    with arcpy.da.UpdateCursor(Streets_network,["LINK_ID",impact_chantier_field_name,debut_chantier_field_name, fin_chantier_field_name, param_field_name,field_name]) as cursor:
        for row in cursor:
            link_id = str(row[0])
            row[1] = chantier_dict[link_id][impact_chantier_field_name]
            row[2] = chantier_dict[link_id][debut_chantier_field_name]
            row[3] = chantier_dict[link_id][fin_chantier_field_name]
            row[4] = chantier_dict[link_id][param_field_name]
            row[5] = chantier_dict[link_id][field_name]            

            cursor.updateRow(row)

    arcpy.management.Delete(fr"{arcpy.env.scratchGDB}\TEMP_Streets_join_chantier")

#-------------- Critere transport public -----------------
def calcNoteTP(nb_run, seuil_bon, seuil_mauv):   
    if nb_run <= seuil_bon :
        return 3
    elif nb_run < seuil_mauv :
        return 2
    elif nb_run >= seuil_mauv :
        return 1
    else : 
        return 3

def calCritereTP(Streets_network, stop_frequency_layer, champ_numRunsPHour, seuils):
    
    param_field_name = "NB_PASSAGE_TP"
    field_name = "Note_ArretTP"
    liste_note_circulation.append(field_name)

    seuils = seuilStringToList(seuils)

    arcpy.AddMessage("Jointure couche : {}".format(stop_frequency_layer)) 
    fldmappings = arcpy.FieldMappings()
    fldmap_link = arcpy.FieldMap()
    fldmap_link.addInputField(Streets_network, "LINK_ID")
    fld_link = fldmap_link.outputField
    fld_link.name = "LINK_ID"
    fldmap_link.outputField = fld_link
    fldmappings.addFieldMap(fldmap_link)
    
    fldmap_nbRun = arcpy.FieldMap()
    fldmap_nbRun.addInputField(stop_frequency_layer, champ_numRunsPHour)
    fld_nbRun = fldmap_nbRun.outputField
    fld_nbRun.name = champ_numRunsPHour
    fldmap_nbRun.outputField = fld_nbRun
    fldmappings.addFieldMap(fldmap_nbRun)

    StopFrequencyLayer_Join = fr"{arcpy.env.scratchGDB}\TEMP_StopFrequencyLayer_Join"
    
    # C'est l'arrêt le plus proche du tronçons qui est considérés (avec une certaine distance de recherche).
    # ATTENTION, cela peut dire qu'un arrêt ne se "connecte" pas avec le bon tronçon selon la configuration des routes.
    arcpy.analysis.SpatialJoin(target_features=stop_frequency_layer,join_features=Streets_network, out_feature_class=StopFrequencyLayer_Join, join_operation="JOIN_ONE_TO_ONE", join_type="KEEP_COMMON",field_mapping=fldmappings,match_option="CLOSEST",search_radius=100)
    
    TP_dict = dict()
    with arcpy.da.SearchCursor(StopFrequencyLayer_Join,["LINK_ID",champ_numRunsPHour]) as cursor :
        for row in cursor:
            link = str(row[0])
            nbRun = row[1]

            #Un linnk peur avoir plusieurs arrêts, c'est la somme de tous qui est considéré pour la notation
            if link in TP_dict.keys():
                TP_dict[link] += nbRun
                continue
            TP_dict[link] = nbRun
    
    arcpy.AddMessage("Calcul champ : {} et {} avec seuils {}".format(param_field_name, field_name, seuils))
    #Ajout des champs si pas existants
    if param_field_name not in [f.name for f in arcpy.ListFields(Streets_network)]:
        arcpy.management.AddField(Streets_network, param_field_name, "LONG")
    if field_name not in [f.name for f in arcpy.ListFields(Streets_network)]:
        arcpy.management.AddField(Streets_network, field_name, "LONG")
    
    #Mise à jour des champs de la couche
    with arcpy.da.UpdateCursor(Streets_network, ["LINK_ID",param_field_name, field_name]) as cursor :
        for row in cursor:
            link = str(row[0])
            if link in TP_dict.keys():
                row[1] = TP_dict[link]
                row[2] = calcNoteTP(TP_dict[link], int(seuils[0]), int(seuils[1]))
            else :
                row[1] = 0
                row[2] = 3
            cursor.updateRow(row)

    arcpy.management.Delete(fr"{arcpy.env.scratchGDB}\TEMP_StopFrequencyLayer_Join")

#----------------------------------------------------------
#-------------- Calcul de la note globale -----------------
#----------------------------------------------------------
def calcNoteGlobale(Streets_network, liste_field_circ, liste_field_access, ratio_hiera, couches_POI, pond_circ, pond_acces):
    
    global note_max, note_min
    note_max = 3
    note_min = 1


    liste_ratio_hiera = ratio_hiera.split(" ")
    liste_ratio_hiera = [float(e) for e in liste_ratio_hiera]
    
    # Transformation du parametre ASrcGIS en dictionary python pour être exploité. Input : "path1 ratio1;path2 ratio2;path3 ratio3;..." 
    couches_list = couches_POI.split(";")
    couches_POI_dict = dict()
    i=0
    for row in couches_list :
        liste = row.rsplit(" ",1)
        couches_POI_dict[i] = {"path" : liste[0], "ratio": float(liste[1])}
        i+=1
    
    POI_count = {}
    for key in couches_POI_dict.keys():
        temp_POI_count_layer = fr"{arcpy.env.scratchGDB}\TEMP_temp_POI_count_layer"
        
        arcpy.analysis.SummarizeNearby(in_features=Streets_network, in_sum_features=couches_POI_dict[key]["path"], out_feature_class=temp_POI_count_layer, distance_type="STRAIGHT_LINE", distances=5, distance_units="METERS")
        with arcpy.da.SearchCursor(temp_POI_count_layer, ["LINK_ID","Point_Count"]) as cursor:
            for row in cursor:
                link_id = str(row[0])
                
                #Compte du nombre de POI par tronçons, multiplié par les ratios entrés par l'utilisateur.
                if link_id in POI_count.keys():
                    POI_count[link_id].append(row[1]*couches_POI_dict[key]["ratio"])
                else :
                    POI_count[link_id] = [row[1]*couches_POI_dict[key]["ratio"]]
        
        arcpy.management.Delete(fr"{arcpy.env.scratchGDB}\TEMP_temp_POI_count_layer")
    
    arcpy.AddMessage("Ajout des champs des moyennes et pondération par troncons")
    #Ajout des champs si pas existants
    field_CIRC_MOY = "CIR_MOY"
    if field_CIRC_MOY not in [f.name for f in arcpy.ListFields(Streets_network)]:
        arcpy.management.AddField(Streets_network, field_CIRC_MOY, "DOUBLE")
    field_CIRC_MOY_pond = "CIR_MOY_pond"
    if field_CIRC_MOY_pond not in [f.name for f in arcpy.ListFields(Streets_network)]:
        arcpy.management.AddField(Streets_network, field_CIRC_MOY_pond, "DOUBLE")
    field_CIRC_MOY_norm = "CIR_MOY_norm"
    if field_CIRC_MOY_norm not in [f.name for f in arcpy.ListFields(Streets_network)]:
        arcpy.management.AddField(Streets_network, field_CIRC_MOY_norm, "DOUBLE")
    global field_ratio_hiera
    field_ratio_hiera = "RATIO_HIE"
    if field_ratio_hiera not in [f.name for f in arcpy.ListFields(Streets_network)]:
        arcpy.management.AddField(Streets_network, field_ratio_hiera, "DOUBLE")


    field_ACC_MOY = "ACC_MOY"
    if field_ACC_MOY not in [f.name for f in arcpy.ListFields(Streets_network)]:
        arcpy.management.AddField(Streets_network, field_ACC_MOY, "DOUBLE") 
    field_ACC_MOY_pond = "ACC_MOY_pond"
    if field_ACC_MOY_pond not in [f.name for f in arcpy.ListFields(Streets_network)]:
        arcpy.management.AddField(Streets_network, field_ACC_MOY_pond, "DOUBLE")
    field_ACC_MOY_norm = "ACC_MOY_norm"
    if field_ACC_MOY_norm not in [f.name for f in arcpy.ListFields(Streets_network)]:
        arcpy.management.AddField(Streets_network, field_ACC_MOY_norm, "DOUBLE")   
    global field_POI_COUNT
    field_POI_COUNT = "POI_COUNT"
    if field_POI_COUNT not in [f.name for f in arcpy.ListFields(Streets_network)]:
        arcpy.management.AddField(Streets_network, field_POI_COUNT, "DOUBLE")

    
    #Mise à jour des champs de la couche
    with arcpy.da.UpdateCursor(Streets_network, liste_field_circ + ["FUNC_CLASS", field_CIRC_MOY, field_CIRC_MOY_pond, field_CIRC_MOY_norm, field_ratio_hiera]) as cursor:
        j = len(liste_field_circ)
            
        for row in cursor:
            moy = sum([row[e] for e in range(j)])/j
            moy_pond = 0
            for i in range(j):
                moy_pond += (row[i]*(pond_circ[i]/sum(pond_circ)))

            moy_norm = (moy_pond-note_min)/(note_max-note_min)
            
            func_class = int(row[j])
            
            if func_class == 1 :
                ratio = liste_ratio_hiera[0]
            elif func_class == 2 :
                ratio = liste_ratio_hiera[1] 
            elif func_class == 3 :
                ratio = liste_ratio_hiera[2]            
            elif func_class == 4 :
                ratio = liste_ratio_hiera[3]
            elif func_class == 5 :
                ratio = liste_ratio_hiera[4]
            
            
            row[j+1] = moy
            row[j+2] = moy_pond
            row[j+3] = moy_norm
            row[j+4] = ratio

            cursor.updateRow(row)


    with arcpy.da.UpdateCursor(Streets_network, liste_field_access + ["LINK_ID", field_ACC_MOY, field_ACC_MOY_pond, field_ACC_MOY_norm, field_POI_COUNT]) as cursor:
        j = len(liste_field_access)
        
        for row in cursor:
            link_id = str(row[j])
            moy = sum([row[e] for e in range(j)])/j
            moy_pond = 0
            for i in range(j):
                moy_pond += (row[i]*(pond_acces[i]/sum(pond_acces)))
            
            moy_norm = (moy-note_min)/(note_max-note_min)
            
            row[j+1] = moy
            row[j+2] = moy_pond
            row[j+3] = moy_norm
            row[j+4] = 1+sum(POI_count[link_id]) if sum(POI_count[link_id]) != 0 else 1 # Une valeur de 1 est mise par défaut dans le conte des POIs, pour éviter que les tronçons sans POI ne valent rien

            cursor.updateRow(row)
    
    
#----------------------------------------------------------
#-------------- Création de la table des indices ----------
#----------------------------------------------------------
def outputTable(Streets_network, nom_table, pond_circ, pond_acc):
    
    df = arcgis_table_to_df(Streets_network, liste_note_circulation+liste_note_accessibilite+[champ_long_Geod,field_ratio_hiera,field_POI_COUNT])
    
    # "Demande" * Longueur : Paramètres de poids pour le calcul des indices
    df["LEN_HIE"] = df[champ_long_Geod]*df[field_ratio_hiera]
    df["LEN_POI"] = df[champ_long_Geod]*df[field_POI_COUNT]
    
    # Champs de la table des indices
    summary_table_field = ["Indicateur","Note_1", "Note_2", "Note_3","Somme_Note", "Somme_Note_norm","Poids_Note_1","Poids_Note_2","Poids_Note_3","Ratio","Indice", "Indice100"]
    
    summary_list = []
    df_sum = df.sum()

    # Calcul pour les indicateurs du groupe circulation
    CIR_Note_1 = 0
    CIR_Note_2 = 0
    CIR_Note_3 = 0
    CIR_indice = 0
    i = 0
    for field in liste_note_circulation:
        
        count_note1 = df[df[field]==1].count()[field]
        count_note2 = df[df[field]==2].count()[field]
        count_note3 = df[df[field]==3].count()[field]
        CIR_Note_1 += count_note1
        CIR_Note_2 += count_note2
        CIR_Note_3 += count_note3
        
        sum_len_hie1 = df[df[field]==1]["LEN_HIE"].sum()
        sum_len_hie2 = df[df[field]==2]["LEN_HIE"].sum()
        sum_len_hie3 = df[df[field]==3]["LEN_HIE"].sum()

        total_row = count_note1+count_note2+count_note3
        total_len_hie = sum_len_hie1+sum_len_hie2+sum_len_hie3 #Normalement égale à df_sum.at["LEN_HIE"]
        somme_note = df_sum.at[field]
        somme_norm = (somme_note-total_row*note_min)/(total_row*note_max-total_row*note_min)
        
        ratio_len_hie = (sum_len_hie1*(1/3)+sum_len_hie2*(2/3)+sum_len_hie3*(3/3))/total_len_hie
        Indice = somme_norm*ratio_len_hie
        CIR_indice += Indice*pond_circ[i]
        
        i+=1
        
        field = field[5:] #Pour enlever le "Note_" dans le noms des champs
        
        row = []
        row.append(field)
        row.append(count_note1)
        row.append(count_note2)
        row.append(count_note3)
        row.append(somme_note)
        row.append(somme_norm)
        row.append(sum_len_hie1)
        row.append(sum_len_hie2)
        row.append(sum_len_hie3)
        row.append(ratio_len_hie)
        row.append(Indice)
        row.append(math.ceil(Indice*100))
        
        summary_list.append(row)
    
    # Calcul pour les indicateurs du groupe accessibilité
    ACC_Note_1 = 0
    ACC_Note_2 = 0
    ACC_Note_3 = 0
    ACC_indice = 0
    i = 0
    for field in liste_note_accessibilite:
        
        count_note1 = df[df[field]==1].count()[field]
        count_note2 = df[df[field]==2].count()[field]
        count_note3 = df[df[field]==3].count()[field]
        ACC_Note_1 += count_note1
        ACC_Note_2 += count_note2
        ACC_Note_3 += count_note3

        sum_len_POI1 = df[df[field]==1]["LEN_POI"].sum()
        sum_len_POI2 = df[df[field]==2]["LEN_POI"].sum()
        sum_len_POI3 = df[df[field]==3]["LEN_POI"].sum()

        total_row = count_note1+count_note2+count_note3
        total_len_POI = sum_len_POI1+sum_len_POI2+sum_len_POI3 #Normalement égale à df_sum.at["LEN_POI"]
        somme_note = df_sum.at[field]
        somme_norm = (somme_note-total_row*note_min)/(total_row*note_max-total_row*note_min)
        
        ratio_len_POI = (sum_len_POI1*(1/3)+sum_len_POI2*(2/3)+sum_len_POI3*(3/3))/total_len_POI
        Indice = somme_norm*ratio_len_POI
        ACC_indice += Indice*pond_acc[i]
        
        i+=1

        field = field[5:] #Pour enlever le "Note_" dans le noms des champs

        row = []
        row.append(field)
        row.append(count_note1)
        row.append(count_note2)
        row.append(count_note3)
        row.append(somme_note)
        row.append(somme_norm)
        row.append(sum_len_POI1)
        row.append(sum_len_POI2)
        row.append(sum_len_POI3)
        row.append(ratio_len_POI)
        row.append(Indice)
        row.append(math.ceil(Indice*100))
        
        summary_list.append(row)
    
    # Notes globales des deux groupes
    summary_list.append(["CIRCULATION", CIR_Note_1, CIR_Note_2, CIR_Note_3, 0,0,0,0,0,0, CIR_indice/sum(pond_circ), math.ceil((CIR_indice/sum(pond_circ))*100)])
    summary_list.append(["ACCESSIBILITE", ACC_Note_1, ACC_Note_2, ACC_Note_3, 0,0,0,0,0,0, ACC_indice/sum(pond_acc), math.ceil((ACC_indice/sum(pond_acc))*100)])
    
    #https://pro.arcgis.com/en/pro-app/latest/arcpy/functions/validatetablename.htm
    nom_table = arcpy.ValidateTableName(nom_table) # a priori pas necessaire, mais au cas ou

    #Création de la table et ajout des données
    note_summary_table = arcpy.management.CreateTable(out_path=f"{workspace}",out_name=nom_table)[0]
    arcpy.management.AddField(note_summary_table, summary_table_field[0], "STRING")
    arcpy.management.AddField(note_summary_table, summary_table_field[1], "LONG")
    arcpy.management.AddField(note_summary_table, summary_table_field[2], "LONG")
    arcpy.management.AddField(note_summary_table, summary_table_field[3], "LONG")
    arcpy.management.AddField(note_summary_table, summary_table_field[4], "LONG")
    arcpy.management.AddField(note_summary_table, summary_table_field[5], "DOUBLE")
    arcpy.management.AddField(note_summary_table, summary_table_field[6], "DOUBLE")
    arcpy.management.AddField(note_summary_table, summary_table_field[7], "DOUBLE")
    arcpy.management.AddField(note_summary_table, summary_table_field[8], "DOUBLE")
    arcpy.management.AddField(note_summary_table, summary_table_field[9], "DOUBLE")
    arcpy.management.AddField(note_summary_table, summary_table_field[10], "DOUBLE")
    arcpy.management.AddField(note_summary_table, summary_table_field[11], "LONG")
    
    with arcpy.da.InsertCursor(note_summary_table, summary_table_field) as cursor:
        for row in summary_list:
            cursor.insertRow(row)
    return note_summary_table


def arcgis_table_to_df(in_fc, input_fields=None, query=""): 
    #Source : https://gist.github.com/d-wasserman/e9c98be1d0caebc2935afecf0ba239a0
    """Function will convert an arcgis table into a pandas dataframe with an object ID index, and the selected
    input fields using an arcpy.da.SearchCursor.
    :param - in_fc - input feature class or table to convert
    :param - input_fields - fields to input to a da search cursor for retrieval
    :param - query - sql query to grab appropriate values
    :returns - pandas.DataFrame"""
    OIDFieldName = arcpy.Describe(in_fc).OIDFieldName
    if input_fields:
        final_fields = [OIDFieldName] + input_fields
    else:
        final_fields = [field.name for field in arcpy.ListFields(in_fc)]
    data = [row for row in arcpy.da.SearchCursor(in_fc,final_fields,where_clause=query)]
    fc_dataframe = pandas.DataFrame(data,columns=final_fields)
    fc_dataframe = fc_dataframe.set_index(OIDFieldName,drop=True)
    return fc_dataframe

def createChart(project, map, layer_name, table_name):
    
    # doc subclass chart arcpy : https://pro.arcgis.com/en/pro-app/latest/arcpy/charts/what-is-the-charts-module.htm

    # A Noter q'il est normalement possible d'ajouter des graphe à un parametre défnit en "output" dans AcrcGIS Pro
    # # doc class parameter arcpy pour .charts sur output : https://pro.arcgis.com/en/pro-app/latest/arcpy/classes/parameter.htm
    # Mais cette méthode ne fonctionne que lorsque le parametrer avec une direction "Output" est "required", mais pas lorsque il est en "Derived"
    # Dans ce cas, l'erreur suivante apparait : 

        # RuntimeError: Can't create chart parameters.

        # The above exception was the direct cause of the following exception:

        # Traceback (most recent call last):
        #   File "C:\Users\Niels\OneDrive - epfl.ch\Documents\EPFL\05_Master\PDME\PDM\Application ArcGis\Projet ArcGIS PRO\Code python\Demo Outil Execution.py", line 1440, in <module>
        #     createChart(param_output_fc, param_output_table, summary_table)
        #   File "C:\Users\Niels\OneDrive - epfl.ch\Documents\EPFL\05_Master\PDME\PDM\Application ArcGis\Projet ArcGIS PRO\Code python\Demo Outil Execution.py", line 1253, in createChart
        #     param_output_fc.charts = chart_liste
        #   File "C:\Program Files\ArcGIS\Pro\Resources\ArcPy\arcpy\arcobjects\_base.py", line 109, in _set
        #     return setattr(self._arc_object, attr_name, cval(val))
        # SystemError: <built-in function setattr> returned a result with an error set
    
    # Pour ce script, une méthode différente à été utilsée
    # 


    #Création de la symbologie  
    lyr = map.listLayers(layer_name)[0]
    sym = lyr.symbology
    sym.updateRenderer("GraduatedColorsRenderer")
    sym.renderer.breakCount = 6
    sym.renderer.colorRamp = project.listColorRamps("Red to Green")[0]
    sym.renderer.classificationField = "CIR_MOY_norm"
    sym.renderer.intervalSize = 0.1
    sym.renderer.classificationMethod = "DefinedInterval"
    

    lyr.symbology = sym


    # Création des raphes de la couche réseau  
    histo_cir = arcpy.charts.Histogram(x="CIR_MOY_pond", binCount=10, showMean=True, showMedian=True, showStandardDeviation=True, title="Distribution Moyenne pondérée CIRCULATION", description="Distribution de la moyenne pondérée des indicateurs du groupe circulation par tronçons")
    histo_cir.xAxis.minimum = 1
    histo_cir.xAxis.maximum = 3
    histo_acc = arcpy.charts.Histogram(x="ACC_MOY_pond", binCount=10, showMean=True, showMedian=True, showStandardDeviation=True, title="Distribution Moyenne pondérée ACCESSIBILITE", description="Distribution de la moyenne pondérée des indicateurs du groupe accessibilité par tronçons")
    histo_acc.xAxis.minimum = 1
    histo_acc.xAxis.maximum = 3
    scatter = arcpy.charts.Scatter(x="CIR_MOY", xTitle="Moyenne groupe circulation", y="ACC_MOY", yTitle="Moyenne groupe accessibilité", splitCategory="FUNC_CLASS", multiSeriesDisplay="grid", miniChartsPerRow=2, showPreviewChart=False, showTrendLine=True, title="Corrélation entre les moyennes non pondérées par tronçons en fonction de la hiérarchie des voies")


    histo_cir.addToLayer(lyr)
    histo_acc.addToLayer(lyr)
    scatter.addToLayer(lyr)

    # Création des raphes de la table
    table = map.listTables(table_name)[0]
    
    stacked_bar_chart = arcpy.charts.Bar(x="Indicateur", y=["Note_1","Note_2","Note_3"], multiSeriesDisplay="stacked100", title="Répartition des notes par indicateur", dataSource=table)
    stacked_bar_chart.color = ["#FF0000","#FCFF00","#6CFF00"]
    stacked_bar_chart.addToLayer(table)
    index_bar_chart = arcpy.charts.Bar(x="Indicateur", y=["Somme_Note_norm","Ratio","Indice"], multiSeriesDisplay="sideBySide", title="Somme normalisée, ratio et indice par indicateur", dataSource=table)
    index_bar_chart.yAxis.minimum = 0
    index_bar_chart.yAxis.maximum = 1
    index_bar_chart.addToLayer(table)
    index100_bar_chart = arcpy.charts.Bar(x="Indicateur", y=["Indice100"], title="Notes globales", dataSource=table)
    index100_bar_chart.yAxis.minimum = 0
    index100_bar_chart.yAxis.maximum = 100
    index100_bar_chart.addToLayer(table)

    

def OutilIndiceLivrabilite(nom_etude, type_vehicule, Streets_ZoneEtude, output_path_GDB, nom_GDB, nom_couche_output, nom_table_output, Cdms, CndMod, CdmsDtmod, Lane,table_seuil, modifier_seuil, modifier_ponderation,  pond_circ, pond_acces, ratio_hierarchie, couches_POI, couche_stationnement, filtre_stat, champ_nb_place, distance_stat, nb_place_defaut, table_speed_data, heure_analyse, source_chantier, filtre_type_here, filtre_impact_here, couche_ext_chantier, champ_debut_chantier, champ_fin_chantier, filtre_date_chantier, filtre_valeur_chantier, stop_frequency_layer, champ_numRunPHour, Gabarit_seuil, Voie_Seuil, TP_Seuil, Obstacle_Seuil, Vitesse_Seuil, Congestion_Seuil, Chantier_Seuil, Horaire_Seuil, Stationnement_Seuil, Pente_Seuil):  # Demo Outil
    
    #clé API HERE
    global apiKey
    apiKey = "kX3yLd1fksu_0JK1UWdva09_c2KmkRGlIzO9KHmkK80"
    
    # Permet de remplacer si une couche avec le nême nom existe déjà 
    arcpy.env.overwriteOutput = True
    
    #Variables utilisées ensuite dans les autres fonctions
    global liste_link_id, describe, champ_long_Geod, workspace
    
    pond_circ = pond_circ.split(" ")
    pond_circ = [float(e) for e in pond_circ]
    pond_acces = pond_acces.split(" ")
    pond_acces = [float(e) for e in pond_acces]
    
    arcpy.SetProgressorLabel("Creation de la geodatabase {}".format(nom_GDB))
    # doc https://pro.arcgis.com/en/pro-app/latest/tool-reference/data-management/create-file-gdb.htm
    workspace = arcpy.management.CreateFileGDB(str(output_path_GDB),nom_GDB)[0]
    arcpy.AddMessage("Geodatabase créée à l'adresse : {}".format(workspace))
    
    arcpy.SetProgressorLabel("Creation de la couche {}".format(nom_couche_output))
    # doc https://pro.arcgis.com/en/pro-app/latest/tool-reference/data-management/copy-features.htm
    arcpy.management.CopyFeatures(in_features=Streets_ZoneEtude, out_feature_class=fr"{workspace}\{nom_couche_output}")
    Streets_ZoneEtude = fr"{workspace}\{nom_couche_output}"

    #variable utilisée ensuite dans le calcul des indicateurs
    liste_link_id = unique_values(Streets_ZoneEtude,["LINK_ID"])
    describe = arcpy.Describe(Streets_ZoneEtude)
    
    arcpy.SetProgressorLabel("Ajout des champs NOM_ETUDE, DATE_ETUDE, TYPE_VEH et LEN_KM_GEO")
    arcpy.AddMessage("Ajout des champs NOM_ETUDE, DATE_ETUDE, TYPE_VEH et LEN_KM_GEO")
    arcpy.management.CalculateField(in_table=Streets_ZoneEtude, field="NOM_ETUDE", expression="'"+nom_etude+"'", field_type="TEXT")    
    arcpy.management.CalculateField(in_table=Streets_ZoneEtude, field="DATE_ETUDE", expression="datetime.datetime.now()", field_type="DATE")
    arcpy.management.CalculateField(in_table=Streets_ZoneEtude, field="TYPE_VEH", expression="'"+type_vehicule+"'", field_type="TEXT")

    champ_long_Geod = "LEN_KM_GEO"
    # Important de choisir "GEODESIC" au lieu de "PLANAR" car les données sont exprimées en coordonnées sphériques
    arcpy.management.CalculateGeometryAttributes(in_features=Streets_ZoneEtude, geometry_property=[[champ_long_Geod,"LENGTH_GEODESIC"]], length_unit="KILOMETERS")
    
    arcpy.SetProgressorLabel("Creation de la couche jointe temporaire Streets_join_CdmsMod")
    arcpy.AddMessage("\n-------- Creation couche jointe CdmsMod --------")
    # Création d'une couche temporaire par jointure de Cdms sur la couche réseau, puis ajout des champs MOD_TYPE et MOD_VAL de la table Cnd
    # La couche résultante contient les tronçon du réseau en étude qui ont une valeur dans la table Cdms
    # Est utilisé pour les indicateurs "Type de Carrefour", "Obstacle", "Gabarit"
    Streets_join_CdmsMod = fr"{arcpy.env.scratchGDB}\TEMP_Streets_join_CdmsMod"
    arcpy.management.CopyFeatures(in_features=Streets_ZoneEtude, out_feature_class=Streets_join_CdmsMod)
    arcpy.management.JoinField(in_data=Streets_join_CdmsMod, in_field="LINK_ID", join_table=Cdms, join_field="LINK_ID")
    # arcpy.gapro.JoinFeatures(target_layer=Streets_ZoneEtude, join_layer=Cdms, output= Streets_join_CdmsMod,join_operation="JOIN_ONE_TO_MANY", attribute_relationship=[["LINK_ID", "LINK_ID"]])
    # JoinFeatures fait du toolbox GeoAnalytics Server qui requiert une license
    
    arcpy.management.JoinField(in_data=Streets_join_CdmsMod, in_field="COND_ID", join_table=CndMod, join_field="COND_ID", fields=["MOD_TYPE", "MOD_VAL"])
    
    arcpy.SetProgressorLabel("Creation de la couche jointe temporaire Streets_join_CdmsDTMod")
    arcpy.AddMessage("\n-------- Creation couche jointe CdmsDTMod --------")
    # Création d'une couche temporaire par jointure de CdmsDtmod sur la couche réseau, puis ajout des champs AR_AUTO, AR_TRUCK, AR_DELIVER de la table Cdms
    # La couche résultante contient les tronçon du réseau en étude qui ont une valeur dans la table CdmsDtMod
    # Est utilisé pour l'indicateur Horaire
    Streets_join_CdmsDTMod = fr"{arcpy.env.scratchGDB}\TEMP_Streets_join_CdmsDTMod"
    arcpy.management.CopyFeatures(in_features=Streets_ZoneEtude, out_feature_class=Streets_join_CdmsDTMod)
    arcpy.management.JoinField(in_data=Streets_join_CdmsDTMod, in_field="LINK_ID", join_table=CdmsDtmod, join_field="LINK_ID")
    # arcpy.gapro.JoinFeatures(target_layer=Streets_ZoneEtude, join_layer=CdmsDtmod, output= Streets_join_CdmsDTMod,join_operation="JOIN_ONE_TO_MANY", attribute_relationship=[["LINK_ID", "LINK_ID"]])
    # JoinFeatures fait du toolbox GeoAnalytics Server qui requiert une license

    arcpy.management.JoinField(in_data=Streets_join_CdmsDTMod, in_field="COND_ID", join_table=Cdms, join_field="COND_ID", fields=["AR_AUTO","AR_TRUCKS","AR_DELIVER"])


    arcpy.SetProgressorLabel("Calcul indicateur 'Voie de circulation' (1/11)")
    arcpy.AddMessage("\n-------- Calcul indicateur 'Voie de circulation' (1/11) --------")
    if type_vehicule == "VC" :
        calcCritereVoieVelo(Streets_network=Streets_ZoneEtude, table_lane=Lane)   
    else :
        calcCritereVoie(Streets_network=Streets_ZoneEtude, seuils=Voie_Seuil)
    
    arcpy.SetProgressorLabel("Calcul indicateur 'Arret TP' (2/11)")
    arcpy.AddMessage("\n-------- Calcul indicateur 'Arret TP' (2/11) --------")
    calCritereTP(Streets_network=Streets_ZoneEtude, stop_frequency_layer=stop_frequency_layer, champ_numRunsPHour=champ_numRunPHour, seuils=TP_Seuil)
    
    arcpy.SetProgressorLabel("Calcul indicateur 'Carrefour' (3/11)")
    arcpy.AddMessage("\n-------- Calcul indicateur 'Carrefour' (3/11) --------")
    calcCritereCarrefour(Streets_network=Streets_ZoneEtude, Streets_join_CdmsMod=Streets_join_CdmsMod)

    arcpy.SetProgressorLabel("Calcul indicateur 'Obstacle' (4/11)")
    arcpy.AddMessage("\n-------- Calcul indicateur 'Obstacle' (4/11) --------")
    calcCritereObstacle(Streets_network=Streets_ZoneEtude, Streets_join_CdmsMod=Streets_join_CdmsMod, seuils=Obstacle_Seuil)

    arcpy.SetProgressorLabel("Calcul indicateur 'Vitesse' (5/11)")
    arcpy.AddMessage("\n-------- Calcul indicateur 'Vitesse' (5/11) --------")
    calcCritereVitesse(Streets_network=Streets_ZoneEtude,seuils=Vitesse_Seuil)
    
    arcpy.SetProgressorLabel("Calcul indicateur 'Congestion' (6/11)")
    arcpy.AddMessage("\n-------- Calcul indicateur 'Congestion' (6/11) --------")
    arcpy.AddMessage("Heure d'analyse : {}".format(heure_analyse))
    calcCritereCongestion(Streets_network=Streets_ZoneEtude,table_speed_data=table_speed_data, heure_analyse=heure_analyse, seuils=Congestion_Seuil)

    arcpy.SetProgressorLabel("Calcul indicateur 'Chantier' (7/11)")
    arcpy.AddMessage("\n-------- Calcul indicateur 'Chantier' (7/11) --------")
    arcpy.AddMessage("Source données chantier : {}".format(source_chantier))
    if source_chantier == "HERE" :
        calcCritereChantierHere(Streets_network=Streets_ZoneEtude, filtre_type=filtre_type_here, filtre_impact=filtre_impact_here,seuils=Chantier_Seuil)

    else:
        calcCritereChantierExt(Streets_network=Streets_ZoneEtude,couche_ext_chantier=couche_ext_chantier,champ_debut_chantier=champ_debut_chantier, champ_fin_chantier=champ_fin_chantier,filtre_date_chantier=filtre_date_chantier,filtre_valeur_chantier=filtre_valeur_chantier,seuils=Chantier_Seuil)
    

    arcpy.SetProgressorLabel("Calcul indicateur 'Gabarit' (8/11)")
    arcpy.AddMessage("\n-------- Calcul indicateur 'Gabarit' (8/11) --------")
    calcCritereGabarit(Streets_network=Streets_ZoneEtude, Streets_join_CdmsMod=Streets_join_CdmsMod, seuils=Gabarit_seuil )
     
    arcpy.SetProgressorLabel("Calcul indicateur 'Horaire' (9/11)")
    arcpy.AddMessage("\n-------- Calcul indicateur 'Horaire' (9/11) --------")
    calcCritereHoraire(Streets_network=Streets_ZoneEtude, Streets_join_CdmsDTMod=Streets_join_CdmsDTMod, seuils=Horaire_Seuil)

    arcpy.SetProgressorLabel("Calcul indicateur 'Stationnement' (10/11)")
    arcpy.AddMessage("\n-------- Calcul indicateur 'Stationnement' (10/11) --------")
    calcCritereStationnement(Streets_network=Streets_ZoneEtude, couche_stationnement=couche_stationnement, filtre_stat=filtre_stat, champ_nb_place=champ_nb_place, distance=distance_stat,nb_defaut=nb_place_defaut, seuils=Stationnement_Seuil)
    
    arcpy.SetProgressorLabel("Calcul indicateur 'Pente' (11/11)")
    arcpy.AddMessage("\n-------- Calcul indicateur 'Pente' (11/11) --------")
    calcCriterePente(Streets_network=Streets_ZoneEtude, seuils=Pente_Seuil) 


    
    arcpy.SetProgressorLabel("Calcul moyennes par troncons")
    arcpy.AddMessage("\n-------- Calcul moyennes par troncons --------")
    calcNoteGlobale(Streets_network=Streets_ZoneEtude, liste_field_circ=liste_note_circulation, liste_field_access=liste_note_accessibilite, ratio_hiera=ratio_hierarchie, couches_POI=couches_POI, pond_circ=pond_circ, pond_acces=pond_acces)
    
    arcpy.SetProgressorLabel("Calcul Table statistiques, notes et indicateurs globaux")
    arcpy.AddMessage("\n-------- Calcul Table statistiques, notes et indicateurs globaux --------")
    summary_table = outputTable(Streets_network=Streets_ZoneEtude, nom_table=nom_table_output, pond_circ=pond_circ,pond_acc=pond_acces)

    #Ajout de la couche réseau et de la table à la carte
    p = arcpy.mp.ArcGISProject("current")
    m = p.activeMap
    if m is None :
        p.createMap("Map")
        m = p.listMaps("Map")[0]
    layer = arcpy.management.MakeFeatureLayer(in_features=Streets_ZoneEtude, out_layer=nom_couche_output, workspace=workspace)[0]
    m.addLayer(layer)
    m.addTable(arcpy.mp.Table(summary_table))

    arcpy.SetProgressorLabel("Application symbologie et Création des graphiques")
    arcpy.AddMessage("\n-------- Application de la symbologie et Création des graphiques --------")
    createChart(p, m, nom_couche_output, nom_table_output)


    # Suppression des couches temporaires de la scratchGDB
    arcpy.AddMessage("\n-------- Suppression des couches temporaires de scratchGDB --------") 
    arcpy.management.Delete(fr"{arcpy.env.scratchGDB}\TEMP_Streets_join_CdmsMod")
    arcpy.management.Delete(fr"{arcpy.env.scratchGDB}\TEMP_Streets_join_CdmsDTMod")
    
    arcpy.env.workspace = arcpy.env.scratchGDB
    for scratch_fc in arcpy.ListFeatureClasses() :
        arcpy.management.Delete(fr"{arcpy.env.scratchGDB}\{scratch_fc}")





if __name__ == '__main__':

    arcpy.SetProgressor("default", "Démarrage")
    

    OutilIndiceLivrabilite(*argv[1:])
    
