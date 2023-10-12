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

def parse_combined_xsd(master_xsd_path, imported_xsd_paths):
    # Parse the master XSD
    with open(master_xsd_path, "r") as file:
        master_tree = etree.parse(file)

    # Extract namespaces from the master XSD
    master_namespaces = dict([node for _, node in etree.iterparse(master_xsd_path, events=["start-ns"])])

    # Add elements and complexTypes from the imported XSDs to the master XSD tree
    for xsd_path in imported_xsd_paths:
        with open(xsd_path, "r") as file:
            imported_tree = etree.parse(file)
        for elem in imported_tree.xpath('//xs:element | //xs:complexType | //xs:simpleType', namespaces=master_namespaces):
            master_tree.getroot().append(elem)

    return master_tree, master_namespaces

def parse_xsd_to_layers(xsd_tree, namespaces):
    # Lists to hold DataFrames for each layer
    layer_1_df = None
    layer_2_df = None
    layer_3_df = None

    # Function to create DataFrame structure from complex type, include documentation, optional/mandatory status, and restrictions
    def create_dataframe_from_elements(complex_types):
        columns = []
        docs = []
        optional_status = []
        restrictions = []
        
        for complex_type in complex_types:
            for elem in complex_type.xpath('.//xs:element', namespaces=namespaces):
                column_name = elem.get("name")
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

        return pd.DataFrame([docs, optional_status, restrictions], columns=columns, index=["Documentation", "Optionality", "Enumerations"])

    # Layer 1: Non-repeating complex types combined into a single DataFrame
    non_repeating_types = ["MessageSpec_Type", "PaymentDataBody_Type", "PSP_Type", "PSPId_Type", "ReportingPeriod_Type", "Representative_Type"]
    complex_type_elements = [xsd_tree.xpath(f'//xs:complexType[@name="{ctype}"]', namespaces=namespaces)[0] for ctype in non_repeating_types]
    layer_1_df = create_dataframe_from_elements(complex_type_elements)

    # Layer 2: ReportedPayee_Type and its related complex types combined into a single DataFrame
    related_types = ["ReportedPayee_Type", "AccountIdentifier_Type", "TAXIdentifier_Type", "PayerMS_Type"]
    complex_type_elements = [xsd_tree.xpath(f'//xs:complexType[@name="{ctype}"]', namespaces=namespaces)[0] for ctype in related_types]
    layer_2_df = create_dataframe_from_elements(complex_type_elements)

    # Layer 3: ReportedTransaction_Type
    reported_transaction_types = ["ReportedTransaction_Type"]
    reported_transaction_elements = [xsd_tree.xpath(f'//xs:complexType[@name="{ctype}"]', namespaces=namespaces)[0] for ctype in reported_transaction_types]
    layer_3_df = create_dataframe_from_elements([reported_transaction_elements])

    return layer_1_df, layer_2_df, layer_3_df

# Export DataFrames to Excel
def export_to_excel(layer_1_df, layer_2_df, layer_3_df, filename="E:\Eveything Else\OneDrive\Documents\Python Scripts\layers_output.xlsx"):
    with pd.ExcelWriter(filename) as writer:
        layer_1_df.to_excel(writer, sheet_name="Layer_1", index=False)
        layer_2_df.to_excel(writer, sheet_name="Layer_2", index=False)
        layer_3_df.to_excel(writer, sheet_name="Layer_3", index=False)


if __name__ == "__main__":
    # Combine master XSD with imported XSDs
    combined_tree, combined_namespaces = parse_combined_xsd("E:\Eveything Else\OneDrive\Documents\Python Scripts\PaymentData.xsd", ["E:\Eveything Else\OneDrive\Documents\Python Scripts\commontypes.xsd", "E:\Eveything Else\OneDrive\Documents\Python Scripts\isotypes.xsd"])

    # Re-run the corrected parsing function with the re-uploaded XSD
    layer_1, layer_2, layer_3 = parse_xsd_to_layers(combined_tree, combined_namespaces)

    # Re-export the corrected DataFrames to Excel
    export_to_excel(layer_1, layer_2, layer_3)
    