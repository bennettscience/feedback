from marshmallow import fields, Schema
import marshmallow.utils

class UserLoginSchema(Schema):
    id = fields.Int()


class UserSchema(Schema):
    id = fields.Int(dump_only=True)
    name = fields.Str()
    last_name = fields.Str()
    first_name = fields.Str()
    user_type = fields.Str()
    email = fields.Str()
    enrollments = fields.Pluck("self", "name", many=True)
    assessments = fields.List(fields.Nested("StandardAttemptSchema"))


class OutcomeScore(Schema):
    outcome_canvas_id = fields.Int()
    score = fields.Str()


class CourseSchema(Schema):
    id = fields.Int(dump_only=True)
    name = fields.Str()
    standards = fields.List(fields.Nested("StandardListSchema"), dump_only=True)
    # assignments = fields.List(fields.Nested(lambda: AssignmentSchema(exclude=('watching',))))
    enrollments = fields.List(fields.Nested(lambda: UserSchema(exclude=('enrollments',))))


class UserAssignment(Schema):
    id = fields.Int(dump_only=True)
    user = fields.Nested(UserSchema)
    assignment = fields.Nested("AssignmentSchema")
    score = fields.Int()
    occurred = fields.DateTime()


class CreateAssignmentSchema(Schema):
    canvas_id = fields.Int(required=True)
    course_id = fields.Int(required=True)
    name = fields.Str(required=True)
    points_possible = fields.Int(requried=True)


class AssignmentSchema(Schema):
    type = fields.Str(dump_default='assignment')
    id = fields.Int(dump_only=True)
    canvas_id = fields.Int()
    name = fields.Str()
    watching = fields.Nested(lambda: OutcomeListSchema(only=('id', 'name',)), dump_only=True)
    mastery = fields.Nested(UserAssignment(exclude=('assignment','user')))


class CanvasSyncServiceOutcome(Schema):
    id = fields.Int(dump_only=True)
    name = fields.Str(dump_only=True)


class StandardListSchema(Schema):
    id = fields.Int(dump_only=True)
    name = fields.Str()
    description = fields.Str()

class StandardSchema(Schema):
    id = fields.Int(dump_only=True)
    name = fields.Str()
    score = fields.Float(dump_only=True)
    attempts = fields.List(fields.Nested("StandardAttemptSchema"))

class StandardAttemptSchema(Schema):
    id = fields.Int(dump_only=True)
    user = fields.Nested(UserSchema(exclude=['enrollments', 'assessments']))
    score = fields.Int()
    occurred = fields.DateTime(format="%Y-%m-%d")
    comments = fields.Str()
    standard = fields.Nested(StandardSchema(exclude=['attempts']))
    assignment = fields.Str()
