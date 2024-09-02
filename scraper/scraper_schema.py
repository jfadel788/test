from marshmallow import Schema, fields, ValidationError

class InputSchema(Schema):
    url = fields.Url(required=True, error_messages={"required": "URL is required", "invalid": "Invalid URL"})
    description = fields.Str(required=True, error_messages={"required": "Description is required"})
    price = fields.Float(required=True, error_messages={"required": "Price is required", "invalid": "Price must be a number"})

