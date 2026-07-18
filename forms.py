"""
Flask-WTF forms. CSRF protection is automatic for every form here
because the app enables CSRFProtect globally (see extensions.py).
"""
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, FileRequired, MultipleFileField
from wtforms import StringField, PasswordField, BooleanField, SubmitField, IntegerField, SelectField
from wtforms.validators import DataRequired, Email, EqualTo, Length, NumberRange, Optional


class RegisterForm(FlaskForm):
    name = StringField("Full name", validators=[DataRequired(), Length(min=2, max=120)])
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=255)])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=8)])
    confirm_password = PasswordField(
        "Confirm password",
        validators=[DataRequired(), EqualTo("password", message="Passwords must match")],
    )
    submit = SubmitField("Create account")


class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    remember_me = BooleanField("Remember me")
    submit = SubmitField("Log in")


class ProfileForm(FlaskForm):
    name = StringField("Full name", validators=[DataRequired(), Length(min=2, max=120)])
    submit = SubmitField("Save changes")


class ChangePasswordForm(FlaskForm):
    current_password = PasswordField("Current password", validators=[DataRequired()])
    new_password = PasswordField("New password", validators=[DataRequired(), Length(min=8)])
    confirm_new_password = PasswordField(
        "Confirm new password",
        validators=[DataRequired(), EqualTo("new_password")],
    )
    submit = SubmitField("Update password")


# ---------- Tool forms ----------

class MultiPDFUploadForm(FlaskForm):
    files = MultipleFileField(
        "PDF files", validators=[FileRequired(), FileAllowed(["pdf"], "PDF files only")]
    )
    submit = SubmitField("Upload")


class SinglePDFUploadForm(FlaskForm):
    file = FileField(
        "PDF file", validators=[FileRequired(), FileAllowed(["pdf"], "PDF files only")]
    )
    submit = SubmitField("Upload")


class SplitForm(SinglePDFUploadForm):
    ranges = StringField(
        "Page ranges (e.g. 1-3,5,7-9)", validators=[DataRequired()]
    )


class CompressForm(SinglePDFUploadForm):
    quality = SelectField(
        "Compression level",
        choices=[("low", "Low (best quality)"), ("medium", "Medium"), ("high", "High (smallest file)")],
        default="medium",
    )


class RotateForm(SinglePDFUploadForm):
    angle = SelectField("Rotate by", choices=[("90", "90°"), ("180", "180°"), ("270", "270°")], default="90")


class WatermarkForm(SinglePDFUploadForm):
    text = StringField("Watermark text", validators=[DataRequired(), Length(max=100)])
    opacity = IntegerField("Opacity (%)", default=30, validators=[NumberRange(min=5, max=100)])


class PageNumbersForm(SinglePDFUploadForm):
    position = SelectField(
        "Position",
        choices=[("bottom-center", "Bottom center"), ("bottom-right", "Bottom right"), ("top-right", "Top right")],
        default="bottom-center",
    )
    start_number = IntegerField("Start at", default=1, validators=[NumberRange(min=1)])


class ProtectForm(SinglePDFUploadForm):
    password = PasswordField("Set password", validators=[DataRequired(), Length(min=4)])


class UnlockForm(SinglePDFUploadForm):
    password = PasswordField("Current password", validators=[DataRequired()])


class ExtractDeleteForm(SinglePDFUploadForm):
    pages = StringField("Pages (e.g. 1-3,5)", validators=[DataRequired()])


class ImageToPDFForm(FlaskForm):
    files = MultipleFileField(
        "Images", validators=[FileRequired(), FileAllowed(["jpg", "jpeg", "png"], "Images only")]
    )
    submit = SubmitField("Convert to PDF")


class OCRForm(SinglePDFUploadForm):
    language = SelectField("Language", choices=[("eng", "English"), ("fra", "French"), ("spa", "Spanish")], default="eng")
