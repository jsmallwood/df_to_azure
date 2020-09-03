import logging
from azure.mgmt.datafactory.models import *
from src.functions import print_item
from src.parse_settings import get_settings
from azure.common.credentials import ServicePrincipalCredentials
from azure.mgmt.datafactory import DataFactoryManagementClient
from azure.mgmt.resource import ResourceManagementClient
from azure.storage.blob import BlobServiceClient


logging.getLogger(__name__).setLevel(logging.INFO)

adf_settings = get_settings("settings/yml/adf_settings.yml")
azure_settings = get_settings("settings/yml/azure_settings.yml")


def create_adf_client():
    credentials = ServicePrincipalCredentials(
        client_id=azure_settings["client_id"], secret=azure_settings["secret"], tenant=azure_settings["tenant"]
    )

    adf_client = DataFactoryManagementClient(credentials, azure_settings["subscription_id"])

    return adf_client


def create_resource_client():
    credentials = ServicePrincipalCredentials(
        client_id=azure_settings["client_id"], secret=azure_settings["secret"], tenant=azure_settings["tenant"]
    )
    resource_client = ResourceManagementClient(credentials, azure_settings["subscription_id"])

    return resource_client


def create_resourcegroup():

    resource_client = create_resource_client()
    rg_params = {"location": adf_settings["rg_location"]}
    rg = resource_client.resource_groups.create_or_update(adf_settings["rg_name"], rg_params)
    print_item(rg)


def create_datafactory():

    df_resource = Factory(location=adf_settings["rg_location"])
    adf_client = create_adf_client()
    df = adf_client.factories.create_or_update(adf_settings["rg_name"], adf_settings["df_name"], df_resource)
    print_item(df)

    while df.provisioning_state != "Succeeded":
        df = adf_client.factories.get(rg_name, df_name)
        logging.info(f"datafactory {adf_settings['df_name']} created!")


def create_blob_service_client():
    connect_str = "DefaultEndpointsProtocol=https;AccountName={};AccountKey={}".format(
        adf_settings["ls_blob_account_name"], adf_settings["ls_blob_account_key"]
    )

    blob_service_client = BlobServiceClient.from_connection_string(connect_str)

    return blob_service_client


def create_blob_container():
    blob_service_client = create_blob_service_client()
    try:
        blob_service_client.create_container(adf_settings["ls_blob_container_name"])
    except:
        logging.info("Container already exists.")


def create_linked_service_sql():
    conn_string = SecureString(
        value=f"integrated security=False;encrypt=True;connection timeout=30;data source={adf_settings['ls_sql_server_name']};initial catalog={adf_settings['ls_sql_database_name']};user id={adf_settings['ls_sql_database_user']};password={adf_settings['ls_sql_database_password']}"
    )

    ls_azure_sql = AzureSqlDatabaseLinkedService(connection_string=conn_string)
    adf_client = create_adf_client()

    adf_client.linked_services.create_or_update(
        adf_settings["rg_name"], adf_settings["df_name"], adf_settings["ls_sql_name"], ls_azure_sql
    )


def create_linked_service_blob():
    storage_string = SecureString(
        value=f"DefaultEndpointsProtocol=https;AccountName={adf_settings['ls_blob_account_name']};AccountKey={adf_settings['ls_blob_account_key']}"
    )

    ls_azure_blob = AzureStorageLinkedService(connection_string=storage_string)
    adf_client = create_adf_client()
    ls = adf_client.linked_services.create_or_update(
        adf_settings["rg_name"], adf_settings["df_name"], adf_settings["ls_blob_name"], ls_azure_blob
    )