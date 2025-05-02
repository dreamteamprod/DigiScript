from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text

from models.models import db


class UserOverridesRegistry:
    _registry = {}

    # Type mapping for SQLAlchemy column types to Python types
    _type_map = {
        String: {"name": "String", "python_type": str},
        Text: {"name": "String", "python_type": str},
        Integer: {"name": "Integer", "python_type": int},
        Boolean: {"name": "Boolean", "python_type": bool},
        Float: {"name": "Float", "python_type": float},
        DateTime: {"name": "DateTime", "python_type": str},
    }

    @classmethod
    def registry(cls):
        return cls._registry

    @classmethod
    def register(cls, settings_fields=None):
        def decorator(model_class):
            # Use the model's __tablename__ as the settings type identifier
            settings_type = model_class.__tablename__

            # Raise an exception if settings_fields is None
            if settings_fields is None:
                raise ValueError(
                    f"settings_fields must be provided for {model_class.__name__}"
                )

            # Get primary key fields
            primary_key_fields = [
                c.name for c in model_class.__table__.columns if c.primary_key
            ]

            # Extract schema
            schema = cls._extract_schema(
                model_class, primary_key_fields, settings_fields
            )

            # Store schema in registry
            cls._registry[settings_type] = {
                "model": model_class,
                "schema": schema,
                "primary_key_fields": primary_key_fields,
                "settings_fields": settings_fields,
            }

            # Add class method for conversion to settings
            @classmethod
            def to_settings_dict(_model_cls, instance=None):
                result = {}

                # Include all fields from schema
                for field_name in cls._registry[settings_type]["schema"].keys():
                    if instance and hasattr(instance, field_name):
                        # Get the value from the instance
                        result[field_name] = getattr(instance, field_name)
                    else:
                        # Get default from schema
                        schema_info = cls._registry[settings_type]["schema"][field_name]
                        result[field_name] = schema_info["default"]
                return result

            # Add the method to the model class
            model_class.to_settings_dict = to_settings_dict

            return model_class

        return decorator

    @classmethod
    def _get_column_type_info(cls, column):
        column_type = type(column.type)

        # Use the actual column type, if this fails then we need to add
        # support for that column type
        return cls._type_map[column_type]

    @classmethod
    def _extract_schema(cls, model_class, primary_key_fields, additional_fields):
        schema = {}

        # Include primary key fields and additional fields
        fields_to_include = primary_key_fields + additional_fields

        for column_name, column in model_class.__table__.columns.items():
            if column_name in fields_to_include:
                type_info = cls._get_column_type_info(column)

                schema[column_name] = {
                    "type_name": type_info["name"],
                    "python_type": type_info["python_type"],
                    "nullable": column.nullable,
                    "default": (
                        column.default.arg if column.default is not None else None
                    ),
                    "primary_key": column.primary_key,
                }

        # Make sure we have the same number of fields in the schema as we do fields requested by
        # the registration
        if len(schema) != len(fields_to_include):
            raise ValueError(
                f"Schema mismatch for {model_class.__name__}. Not all fields included."
            )

        return schema

    @classmethod
    def get_schema(cls, settings_type):
        if settings_type not in cls._registry:
            raise ValueError(f"Settings type '{settings_type}' not registered")
        return cls._registry[settings_type]["schema"]

    @classmethod
    def validate(cls, settings_type, data):
        if settings_type not in cls._registry:
            raise ValueError(f"Settings type '{settings_type}' not registered")

        schema = cls._registry[settings_type]["schema"]
        errors = []

        # Check that all fields are present
        for field in schema:
            if field not in data:
                errors.append(f"Missing required field: {field}")

        # Validate field types
        for field, value in data.items():
            if field in schema:
                expected_type = schema[field]["python_type"]
                if not isinstance(value, expected_type):
                    errors.append(
                        f"Field {field} must be a {schema[field]['type_name'].lower()}"
                    )
            else:
                errors.append(f"Unknown field: {field}")

        return errors

    @classmethod
    def is_registered(cls, settings_type):
        if isinstance(settings_type, db.Model):
            settings_type = settings_type.__tablename__
        return settings_type in cls._registry
