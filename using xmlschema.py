from xmlschema import XMLSchema
from pprint import pprint

schema = XMLSchema.meta_schema.decode('/Users/davidwren/Library/CloudStorage/OneDrive-Personal/Documents/Python/XSDParser/PaymentData.xsd')

pprint (schema)