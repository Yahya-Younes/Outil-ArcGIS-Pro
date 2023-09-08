# -*- coding: utf-8 -*-
"""
Generated for ArcGIS Pro Toolbox on : 2023-07-31 
Version 0.1
Author Yahya YOUNES

"""
import arcpy
import os
import sys

def NetworkDatasetCreationTool(feature_dataset,
                               Input_GTFS_Folder,
                               Network_Dataset_Template):
    


    # To allow overwriting outputs change overwriteOutput option to True.
    arcpy.env.overwriteOutput = True
    
    # Check out any necessary licenses.
    arcpy.CheckOutExtension("Network")

    # Process: GTFS To Public Transit Data Model (GTFS To Public Transit Data Model) (transit)

    _ = arcpy.transit.GTFSToPublicTransitDataModel(in_gtfs_folders=[Input_GTFS_Folder],
                                                target_feature_dataset=feature_dataset,
                                                interpolate="NO_INTERPOLATE", append="NO_APPEND")
    arcpy.AddMessage("Importation du(es) GTFS vers le modèle de données de transport en commun")
    

    # Process: Connect Public Transit Data Model
    # To Streets (Connect Public Transit Data Model To Streets) (transit)

    # Get Streets from the input feature dataset
    Streets = fr"{feature_dataset}\Streets"

    _ = arcpy.transit.ConnectPublicTransitDataModelToStreets(
        target_feature_dataset=feature_dataset,
        in_streets_features=Streets,
        search_distance="100 Meters",
        expression="AR_PEDEST <> 'Y'")
    
    arcpy.AddMessage("Connexion des données de transport en commun aux rues")


    # Process: Create Network Dataset (Create Network Dataset) 
    # Create the network dataset using the template
    _ = arcpy.na.CreateNetworkDatasetFromTemplate(Network_Dataset_Template,
                                                  feature_dataset)
    arcpy.AddMessage("Création d'un jeu de données réseau à partir d'un modèle")

    # Process: Build Network (Build Network) (na)
    Aratchof = f"{feature_dataset}\\TransitNetwork_ND"

    _ = arcpy.na.BuildNetwork(Aratchof)
    arcpy.AddMessage("Le réseau de transport multimodal est créé avec succès dans {}".format(feature_dataset))


if __name__ == '__main__':

    arcpy.env.overwriteOutput = True
 
    feature_dataset = arcpy.GetParameter(0)
    Input_GTFS_Folder = arcpy.GetParameter(1)
    Network_Dataset_Template = arcpy.GetParameterAsText(2)

    path_todir = arcpy.Describe(
            f"{feature_dataset}").catalogPath
    
    Workspace = os.path.dirname(path_todir)

    # Feature class names to check
    feature_class_names = ["Stops", "LineVariantElements", "StopsOnStreets","StopConnectors"]

    # Check for the presence of specific feature classes in the workspace
    for dirpath, dirnames, _ in arcpy.da.Walk(Workspace, datatype="FeatureDataset"):
        for feature_class_name in feature_class_names:
            feature_class_path = os.path.join(dirpath, feature_class_name)
            if arcpy.Exists(feature_class_path):
                arcpy.AddError(f"Il existe déjà une couche {feature_class_name} dans le dataset {dirpath}, veuillez la supprimer ou utiliser une autre géodatabase.")
                sys.exit(1)

    # Global Environment settings
    NetworkDatasetCreationTool(feature_dataset, Input_GTFS_Folder, Network_Dataset_Template)