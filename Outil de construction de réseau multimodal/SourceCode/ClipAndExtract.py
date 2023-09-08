# -*- coding: utf-8 -*-
"""
Generated for ArcGIS Pro Toolbox on : 2023-07-31 
Version 0.1
Author Yahya YOUNES

"""


import arcpy
import os
import sys


def create_feature_dataset(Workspace, feature_dataset):

    # Si le champ feature dataset est vide donc on crée rien
    if not feature_dataset :
        return
    
    # Si le champ feature dataset n'est pas vide mais que le nom choisi existe déjà dans la gdb
    elif arcpy.Exists(Workspace + "\\" + feature_dataset):
        arcpy.AddMessage("Jeu de classes d'entités: {} déjà existant ".format(feature_dataset))
        feature_dataset = arcpy.Describe(f"{Workspace}\\{feature_dataset}").catalogPath
        return(feature_dataset)
    
    # Si tu veux créer un feature dataset mais tu veux pas de projection spécial on fait par défaut WGS 1984
    if not projection_list :
        spatial_reference = arcpy.SpatialReference(4326)
        # Create the feature dataset
        arcpy.CreateFeatureDataset_management(Workspace,
                                            feature_dataset,
                                            spatial_reference)
        arcpy.AddMessage("Création du jeu de classes d'entités: {} ".format(feature_dataset))
        feature_dataset = arcpy.Describe(
            f"{Workspace}\\{feature_dataset}").catalogPath
        return feature_dataset
    
    # Si tu veux créer un feature dataset mais tu veux une projection spécial on crée la feature dataset dans cette projection
    spatial_reference_custom = arcpy.SpatialReference(3857)
    # Create the feature dataset
    arcpy.CreateFeatureDataset_management(Workspace,
                                        feature_dataset,
                                        spatial_reference_custom)
    arcpy.AddMessage("Création du jeu de classes d'entités: {} dans le système {} ".format(feature_dataset,projection_list))
    feature_dataset = arcpy.Describe(
        f"{Workspace}\\{feature_dataset}").catalogPath
    return feature_dataset


def clipExtractStreet(Streets, couche, champ, zones,nom_couche):  

    # Permet de remplacer une couche existante
    arcpy.env.overwriteOutput = True
    
    # Création du filtre de la couche des zones en fonction du choix des paramètres en entrée
    where_clause = ""
    for zone in zones:
        zone = zone.replace("'","''") # Pour les noms ayant des apostrophes
        where_clause += fr"{champ} = '{zone}' OR "
    where_clause = where_clause[:-3]
    
    arcpy.AddMessage("Zones sélectionnées : {}".format(zones))
    # Selection parmi la couche des zones
    Selection_Zone, Count = arcpy.management.SelectLayerByAttribute(in_layer_or_view=couche,where_clause=where_clause)

    

    Streets_ZoneClip = fr"{arcpy.env.scratchGDB}\Streets_ZoneClip"
    Streets_select, Count = arcpy.management.SelectLayerByAttribute(in_layer_or_view=Streets,where_clause="AR_AUTO = 'N' And AR_BUS = 'N' And AR_TAXIS = 'N' And AR_CARPOOL = 'N' And AR_PEDEST = 'Y' And AR_TRUCKS = 'N' And AR_TRAFF = 'N' And AR_DELIV = 'N' And AR_MOTOR = 'N'", invert_where_clause="INVERT")
    arcpy.analysis.PairwiseClip(in_features=Streets_select, clip_features=Selection_Zone, out_feature_class=Streets_ZoneClip)

    
    
    field_mapping_street = arcpy.FieldMappings()

    if check_list:
        # Extraction des tronçons : 
        #    En excluant ceux ne pouvant pas être circulé à véhicules
        #    En gardent ceux inclus dans les zones sélectionnées
        arcpy.AddMessage("Extraction de la couche Streets {} et ajout des champs nécessaires pour l'étude d'indice de livrabilité".format(nom_couche))
        Streets_ZoneClip = fr"{arcpy.env.scratchGDB}\Streets_ZoneClip"
        Streets_select, Count = arcpy.management.SelectLayerByAttribute(in_layer_or_view=Streets,where_clause="AR_AUTO = 'N' And AR_BUS = 'N' And AR_TAXIS = 'N' And AR_CARPOOL = 'N' And AR_PEDEST = 'Y' And AR_TRUCKS = 'N' And AR_TRAFF = 'N' And AR_DELIV = 'N' And AR_MOTOR = 'N'", invert_where_clause="INVERT")
        arcpy.analysis.PairwiseClip(in_features=Streets_select, clip_features=Selection_Zone, out_feature_class=Streets_ZoneClip)

        # Mappage des champs pour choisir uniqement ceux utilisés dans l'analyse par la suite.
        # doc https://pro.arcgis.com/en/pro-app/latest/arcpy/classes/fieldmappings.htm
        

        field_list = ["LINK_ID", "ST_NAME", "FUNC_CLASS", "TO_SPD_LIM", "FR_SPD_LIM", "FROM_LANES", "TO_LANES", "LANE_CAT", "DIR_TRAVEL", "PHYS_LANES", "AR_AUTO", "AR_BUS", "AR_PEDEST", "AR_TRUCKS","AR_TRAFF","AR_EMERVEH","AR_MOTOR","ROUNDABOUT"]
        for field in field_list:
            field_map = arcpy.FieldMap()
            field_map.addInputField(Streets, field)
            field_mapping_street.addFieldMap(field_map)
        
    Streets_ZoneClip = fr"{arcpy.env.scratchGDB}\Streets_ZoneClip"
    Streets_select, Count = arcpy.management.SelectLayerByAttribute(in_layer_or_view=Streets)
    arcpy.analysis.PairwiseClip(in_features=Streets_select, clip_features=Selection_Zone, out_feature_class=Streets_ZoneClip)


  

    # Define the output coordinate system (WGS 1984)
    if not projection_list and feature_dataset:
            # La projection pour s'assurer qu'on est en WGS1984 si jamais en ne demande pas de parametre(fatory code = 4326)
        output_coordinate_system = arcpy.SpatialReference(4326)
        Streets_Zone_WGS84 = fr"{Workspace}\{feature_dataset}\{nom_couche}_Temp"
        arcpy.management.Project(in_dataset=Streets_ZoneClip, out_dataset=Streets_Zone_WGS84, out_coor_system=output_coordinate_system)
        arcpy.AddMessage("La couche {} a été projetée en coordonnées WGS 1984 ".format(nom_couche))
        Streets_Zone = fr"{Workspace}\{feature_dataset}\{nom_couche}"
        arcpy.AddMessage("Création de la couche {} à l'emplacement : {}".format(nom_couche,Streets_Zone))
        arcpy.conversion.ExportFeatures(in_features=Streets_Zone_WGS84, out_features=Streets_Zone, field_mapping=field_mapping_street)
        arcpy.management.Delete(Streets_Zone_WGS84)

    elif projection_list and feature_dataset :
        # La projection pour s'assurer qu'on est en WGS 1984 Web Mercator si jamais en ne demande pas de parametre(fatory code = 3857)
        output_coordinate_system = arcpy.SpatialReference(3857)
        Streets_Zone_WGS84_Custom = fr"{Workspace}\{feature_dataset}\{nom_couche}_Temp"
        arcpy.management.Project(in_dataset=Streets_ZoneClip, out_dataset=Streets_Zone_WGS84_Custom, out_coor_system=output_coordinate_system)
        Streets_Zone = fr"{Workspace}\{feature_dataset}\{nom_couche}"
        arcpy.conversion.ExportFeatures(in_features=Streets_Zone_WGS84_Custom, out_features=Streets_Zone, field_mapping=field_mapping_street)
        arcpy.management.Delete(Streets_Zone_WGS84_Custom)
        arcpy.AddMessage("La couche {} a été projetée en coordonnées {} ".format(nom_couche,projection_list))

    elif projection_list and not feature_dataset :
        output_coordinate_system = arcpy.SpatialReference(3857)
        Streets_Zone_WGS84_Custom = fr"{Workspace}\{nom_couche}_Temp"
        arcpy.management.Project(in_dataset=Streets_ZoneClip, out_dataset=Streets_Zone_WGS84_Custom, out_coor_system=output_coordinate_system)
        Streets_Zone = fr"{Workspace}\{nom_couche}"
        arcpy.conversion.ExportFeatures(in_features=Streets_Zone_WGS84_Custom, out_features=Streets_Zone, field_mapping=field_mapping_street)
        arcpy.management.Delete(Streets_Zone_WGS84_Custom)
        arcpy.AddMessage("La couche {} a été projetée en coordonnées {} ".format(nom_couche,projection_list))
    
    
    
    else :
        output_coordinate_system = arcpy.SpatialReference(4326)
        Streets_Zone_WGS84 = fr"{Workspace}\{nom_couche}_Temp"
        arcpy.management.Project(in_dataset=Streets_ZoneClip, out_dataset=Streets_Zone_WGS84, out_coor_system=output_coordinate_system)
        arcpy.AddMessage("La couche {} a été projetée en coordonnées WGS 1984 ".format(nom_couche))
        Streets_Zone = fr"{Workspace}\{nom_couche}"
        arcpy.AddMessage("Création de la couche {} à l'emplacement : {}".format(nom_couche,Streets_Zone))
        arcpy.conversion.ExportFeatures(in_features=Streets_Zone_WGS84, out_features=Streets_Zone, field_mapping=field_mapping_street)
        arcpy.management.Delete(Streets_Zone_WGS84)



    # Permet de donner l'étendue de la couche dans la console
    describe = arcpy.Describe(Streets_Zone)
    xmin = describe.extent.XMin
    xmax = describe.extent.XMax
    ymin = describe.extent.YMin
    ymax = describe.extent.YMax

    arcpy.AddMessage("Étendue de la couche {} \n xmin : {} \n xmax : {} \n ymin : {} \n ymax : {}".format(nom_couche,xmin, xmax, ymin, ymax))
    

        
if __name__ == '__main__':
    
    # Assignation des paramètres dépuis ArcGIS Pro
    streets = arcpy.GetParameterAsText(0)
    couche_zone = arcpy.GetParameterAsText(1)
    champ_nom_zone = arcpy.GetParameterAsText(2)
    zones = arcpy.GetParameter(3)
    nom_couche_extrait = arcpy.GetParameterAsText(4)
    feature_dataset = arcpy.GetParameterAsText(5)
    Workspace = arcpy.GetParameterAsText(6)
    check_list = arcpy.GetParameter(7)
    projection_list = arcpy.GetParameterAsText(8)

      # Vérifier s'il y'a déjà une couche Streets dans la gdb pour afficher un message d'erreur

    for dirpath, dirnames, _ in arcpy.da.Walk(Workspace, datatype="FeatureDataset"):
        for dirname in dirnames:
            dataset_path = os.path.join(dirpath, dirname)
            streets_layer = os.path.join(dataset_path, "Streets")
            if arcpy.Exists(nom_couche_extrait) :
                arcpy.AddError(f"Il existe déjà une couche Streets dans le jeu de classes d'entités {dataset_path}, veuillez la supprimer ou saisir un autre nom de couche extraite.")
                sys.exit(1)

    # Appel des fonctions principales 
    create_feature_dataset(Workspace, feature_dataset)
    clipExtractStreet(streets,couche_zone, champ_nom_zone, zones, nom_couche_extrait)





