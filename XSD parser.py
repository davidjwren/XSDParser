#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#GNU

"""
CESOP CSD Parser v0.1

@author: davidjwren
"""

import numpy as np
import pandas as pd
from lxml import etree

def merge_into_master_v2(master_root, imported_root, namespaces, processed_types=[]):
    """Recursively merge elements and complexTypes from imported xsd into the master xsd."""
    for elem in imported_root.xpath('//xs:element | //xs:complexType | //xs:simpleType', namespaces=namespaces):

        # Check if the complexType is already processed to avoid infinite loops
        if elem.tag.endswith("complexType") and elem.get("name") in processed_types:
            continue

        # Append the element or complexType to the master xsd
        master_root.append(elem)

        # If it's a complexType, explore it further for references to other types
        if elem.tag.endswith("complexType"):
            processed_types.append(elem.get("name"))
            for child_elem in elem.xpath('.//xs:element', namespaces=namespaces):
                type_ref = child_elem.get("type", "").split(":")[-1]  # Get the type without namespace
                if type_ref:  # If this element references another type
                    ref_elem = imported_root.xpath(f'//xs:complexType[@name="{type_ref}"] | //xs:simpleType[@name="{type_ref}"]', namespaces=namespaces)
                    if ref_elem:  # If the referenced type is found in the imported xsd
                        merge_into_master_v2(master_root, ref_elem[0], namespaces, processed_types)



def parse_combined_xsd(master_xsd_path, imported_xsd_paths):
    master_tree = etree.parse(master_xsd_path)
    master_root = master_tree.getroot()
    master_namespaces = dict([node for _, node in etree.iterparse(master_xsd_path, events=["start-ns"])])
    for xsd_path in imported_xsd_paths:
        imported_tree = etree.parse(xsd_path)
        merge_into_master_v2(master_root, imported_tree.getroot(), master_namespaces)

    return master_tree, master_namespaces

def parse_xsd_to_layers_recursive(xsd_tree, namespaces):
    """Function to parse the XSD into layers, extracting all nested elements recursively."""
    layer_dataframes = []

    # Layer specifications
    layers = [
        ["MessageSpec_Type", "PaymentDataBody_Type", "PSP_Type", "PSPId_Type", "ReportingPeriod_Type", "Representative_Type"],
        ["ReportedPayee_Type", "AccountIdentifier_Type", "TAXIdentifier_Type", "PayerMS_Type"],
        ["ReportedTransaction_Type"]
    ]

    # Extract data for each layer
    for layer in layers:
        layer_columns = []
        layer_docs = []
        layer_optional_status = []
        layer_restrictions = []

        for ctype in layer:
            complex_type = xsd_tree.xpath(f'//xs:complexType[@name="{ctype}"]', namespaces=namespaces)
            if complex_type:
                columns, docs, optional_status, restrictions = extract_elements_from_complex_type(complex_type[0], namespaces)
                layer_columns.extend(columns)
                layer_docs.extend(docs)
                layer_optional_status.extend(optional_status)
                layer_restrictions.extend(restrictions)

        # Create DataFrame for the layer
        layer_df = pd.DataFrame([layer_docs, layer_optional_status, layer_restrictions], columns=layer_columns, index=["Documentation", "Optionality", "Enumerations"])
        layer_dataframes.append(layer_df)

    return layer_dataframes


# Function to create DataFrame structure from complex type, include documentation, optional/mandatory status, and restrictions
def extract_elements_from_complex_type(complex_type, namespaces):
    """Recursively extract elements from a complex type."""
    columns = []
    docs = []
    optional_status = []
    restrictions = []

    # Extract elements directly under the complex type
    for elem in complex_type.xpath('.//xs:element', namespaces=namespaces):
        column_name = elem.get("name")
        
        # Avoid duplicate columns
        if column_name in columns:
            continue
        
        columns.append(column_name)
        
        # Documentation
        doc = elem.xpath('xs:annotation/xs:documentation/text()', namespaces=namespaces)
        docs.append(doc[0] if doc else None)
        
        # Optional/Mandatory status
        optional_status.append("optional" if elem.get("minOccurs") == "0" else "mandatory")
        
        # Restrictions (enumerations)
        restriction_elem = elem.xpath('xs:simpleType/xs:restriction', namespaces=namespaces)
        if restriction_elem:
            enumerations = restriction_elem[0].xpath('xs:enumeration/@value', namespaces=namespaces)
            restrictions.append(", ".join(enumerations))
        else:
            restrictions.append(None)

    return columns, docs, optional_status, restrictions


if __name__ == "__main__":
    # Combine master XSD with imported XSDs
    combined_tree, combined_namespaces = parse_combined_xsd("E:\Eveything Else\OneDrive\Documents\Python Scripts\PaymentData.xsd", ["E:\Eveything Else\OneDrive\Documents\Python Scripts\commontypes.xsd", "E:\Eveything Else\OneDrive\Documents\Python Scripts\isotypes.xsd"])
    
    with open("E:\Eveything Else\OneDrive\Documents\Python Scripts\combined_xsd.xsd", "wb") as file:
        file.write(etree.tostring(combined_tree, pretty_print=True))

    # Extract layers recursively
    layer_dfs_recursive = parse_xsd_to_layers_recursive(combined_tree, combined_namespaces)

    # Export the DataFrames to Excel
    with pd.ExcelWriter("E:\Eveything Else\OneDrive\Documents\Python Scripts\layers_output.xlsx") as writer:
        for idx, layer_df in enumerate(layer_dfs_recursive, 1):
            layer_df.to_excel(writer, sheet_name=f'Layer {idx}')
    