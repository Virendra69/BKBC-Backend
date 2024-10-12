import json
import io
from datetime import datetime
import base64
import numpy as np
import os
import cv2
import dlib
import glob
import random
import secrets
from PIL import Image
from .models import *
from .serializer import *
from knox.views import LogoutAllView as KnoxLogoutAllView
from knox.views import LogoutView as KnoxLogoutView
from knox.views import LoginView as KnoxLoginView
from rest_framework.authtoken.serializers import AuthTokenSerializer
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.decorators import api_view
from django.core.mail import EmailMessage
from django.contrib.auth.models import User
from django.core.files.storage import FileSystemStorage
from django.conf import settings
from django.contrib.auth import login, logout
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.http import FileResponse

##################################### Helper Functions #####################################

# Deletes files if they exists
class OverwriteStorage(FileSystemStorage):
    def get_available_name(self, name, *args, **kwargs):
        if self.exists(name):
            self.delete(name)
        return name

# Deletes the captured/uploaded photos and blessing cards
def clearImages(username):
    blessing_card_path = os.path.join(
        settings.STATIC_ROOT, f"blessing_card/blessing_card_{username}.png")
    uploaded_image_path = os.path.join(
        settings.STATIC_ROOT, f"uploaded_photo/uploaded_photo_{username}.png")

    if os.path.exists(blessing_card_path):
        os.remove(blessing_card_path)
    if os.path.exists(uploaded_image_path):
        os.remove(uploaded_image_path)

# Places the light on forehead and removes background from photo
def editPhoto(photo_type, username):
    # Load the model
    detector = dlib.get_frontal_face_detector()
    predictor = dlib.shape_predictor(os.path.join(settings.STATIC_ROOT, "model/shape_predictor_68_face_landmarks.dat"))

    photo_path = os.path.join(settings.STATIC_ROOT, f"{photo_type}/{photo_type}_{username}.png")

    # Read the uploaded photo and remove the empty space
    photo = cv2.imread(photo_path, cv2.IMREAD_UNCHANGED)
    non_zero_pixels = np.argwhere(photo[:, :, 3] > 0)
    top_left = np.min(non_zero_pixels, axis=0)
    bottom_right = np.max(non_zero_pixels, axis=0)
    cropped_image = photo[top_left[0]:bottom_right[0], top_left[1]:bottom_right[1]]
    cv2.imwrite(photo_path, cropped_image, [cv2.IMWRITE_PNG_COMPRESSION, 0])

    # Set the size of icon relative to photo size
    photo = Image.open(photo_path)
    photo_width, photo_height = photo.size
    icon_size = int(min(photo_width, photo_height)*0.2)

    # Resize the icon
    icon_path = os.path.join(settings.STATIC_ROOT, "soul.png")
    icon = Image.open(icon_path)
    icon = icon.resize((icon_size, icon_size))

    # Read the photo and convert to RGB
    photo_cv = cv2.imread(photo_path)
    photo_rgb = cv2.cvtColor(photo_cv, cv2.COLOR_BGR2RGB)

    # Get the faces with points detected on them
    faces = detector(photo_rgb)

    x_center = 0
    y_center = 0

    # Iterate through each face, get the center of forehead, place the icon and save the photo
    for face in faces:
        landmarks = predictor(photo_rgb, face)

        x = (landmarks.part(21).x + landmarks.part(22).x)//2
        y = (landmarks.part(21).y + landmarks.part(22).y)//2

        x_corner = x - (icon.size[1]//2)
        y_corner = y - (icon.size[0]//2)

        photo.paste(icon, (x_corner, y_corner), icon)
        x_center = x
        y_center = y
    photo.save(photo_path, compress_level=0)

    # Return the center coordinates
    return x_center, y_center

# Validate the password
def is_valid_password(password):
    try:
        validate_password(password)
        return True
    except ValidationError:
        return False

# Encode image to Base64 string
def encode_image_to_base64(image_path):
    with open(image_path, 'rb') as img_file:
        img = Image.open(img_file)
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='PNG')
        img_byte_arr = img_byte_arr.getvalue()
        img_base64_str = base64.b64encode(img_byte_arr).decode('utf-8')
        return img_base64_str

# Decode the image from Base64 string
def decode_base64_to_image(base64_str, output_path):
    if ";base64," in base64_str:
        base64_str = base64_str.split(";base64,")[1]
    img_data = base64.b64decode(base64_str)
    img_byte_arr = io.BytesIO(img_data)
    img = Image.open(img_byte_arr)
    img.save(output_path, format='PNG')  # Use PNG for lossless saving

#############################################################################################

################################# KNOX Token Authentication #################################

# POST - Send the username & password and get the token
#      - Use the token for every request of any method by placing the token in the Authorization Header
class LoginView(KnoxLoginView):
    permission_classes = (permissions.AllowAny,)

    def post(self, request, format=None):
        serializer = AuthTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        login(request, user)
        return super(LoginView, self).post(request, format=None)

# GET - Logout user session
class LogoutView(KnoxLogoutView):
    def post(self, request, format=None):
        response = super(LogoutView, self).post(request, format=None)
        logout(request)
        clearImages(request.user.username)
        return Response({"status": "user_session_logged_out"}, status=200)

# GET - Logout user's all sessions
class LogoutAllView(KnoxLogoutAllView):
    def post(self, request, format=None):
        response = super(LogoutAllView, self).post(request, format=None)
        clearImages(request.user.username)
        return Response({"status": "all_user_sessions_logged_out"}, status=200)

#############################################################################################

# GET - Get the total count of blessing cards generated
@api_view(["GET"])
def getTotalCardCountAPI(request):
    total_count = sum([c.count for c in ClickCount.objects.all()])
    return Response({"total_count": total_count})

# GET - Delete the data like uploaded photo and generated blessing cards
@api_view(["GET"])
def clearData(request):
    username = request.user.username
    clearImages(username)
    return Response({"message": "Data cleared successfully"})

# GET - Get the username
@api_view(["GET"])
def getUsernameAPI(request):
    return Response({"username": request.user.username})

# POST - Send username to remove the user and their data
@api_view(["POST"])
def removeUser(request):
    data = json.loads(request.body)
    username = data.get("username")
    remove_data = data.get("remove_data")
    if User.objects.filter(username=username):
        user = User.objects.get(username=username)
        user.delete()
        if remove_data.lower() == "true":
            click_count = ClickCount.objects.get(username=username)
            click_count.delete()
            return Response({"message": f"User: {username} and data has been deleted successfully!"})
        return Response({"message": f"User: {username} has been deleted successfully!"})
    return Response({"message": f"User: {username} is not present!"})

# GET - Get status of whether the user is allowed to access the Admin Panel
#     - Clear the photos uploaded/generated by the user from the folders (save storage space)
@api_view(["GET"])
def uploadPhotoPageAPI(request):
    username = request.user.username
    if username:
        allowed_usernames = ["Virendra", "VishkalaVenture"]
        allowed = False
        if username in allowed_usernames:
            allowed = True
        clearImages(username)
        return Response({"is_admin_panel_access_allowed": allowed})
    return Response({"status": "user_not_logged_in"})

# POST - Create a new user
#      - Get the data about number of blessing card generated by each user
@api_view(["POST"])
def createUser(request):
    allowed_usernames = ["Virendra", "VishkalaVenture"]
    username = request.user.username
    if username in allowed_usernames:
        data = json.loads(request.body)
        new_username = data.get("username")
        new_password = data.get("password")
        if not User.objects.filter(username=new_username).exists():
            if is_valid_password(new_password):
                new_user = User.objects.create_user(
                    username=new_username, password=new_password)
                new_user.save()
                new_click_count_obj = ClickCount.objects.create(
                    username=new_username)
                new_click_count_obj.save()
                return Response({"message": f"New User : {new_username} has been added successfully!!"})
            return Response({"message": "Password should contain Alphabets, Special Characters and Numbers!!"})
        return Response({"message": f"User : {new_username} already exists!!"})
    return Response({"status": "user_not_authorized"})

# GET - Get the data about number of blessing card generated by each user
@api_view(["GET"])
def getUserStatistics(request):
    allowed_usernames = ["Virendra", "VishkalaVenture"]
    username = request.user.username
    if username in allowed_usernames:
        click_count_data = ClickCount.objects.all().order_by('-count')
        click_count_data = ClickCountSerializer(click_count_data, many=True)
        click_count_data = click_count_data.data
        return Response({"user_statistics": click_count_data})
    return Response({"status": "user_not_authorized"})

# POST - Upload the photo by sending base64 encoded photo data
@api_view(["POST"])
def saveUploadedPhotoAPI(request):
    username = request.user.username
    try:
        data = json.loads(request.body)
        photo_base64_str = data.get("photo_base64_str")
        photo_path = os.path.join(
            settings.STATIC_ROOT, f"uploaded_photo/uploaded_photo_{username}.png")
        decode_base64_to_image(photo_base64_str, photo_path)
        return Response({"command": "Open the page to choose between Generate Card or Customize Card"})
    except:
        return Response({"command": "Open the page to re-upload the photo", "status": "Error uploading the photo"})

# GET - Get the languages of default templates
@api_view(["GET"])
def getDefaultTemplateLanguagesAPI(request):
    template_languages = list(os.listdir(
        os.path.join(settings.STATIC_ROOT, "card_templates")))
    template_languages.remove("Custom")
    return Response({"template_languages": template_languages})

# GET - Get the list of names of custom templates
@api_view(["GET"])
def getCustomizedTemplatesNumberAPI(request):
    custom_templates_path = os.path.join(
        settings.STATIC_ROOT, "card_templates/Custom")
    custom_temp_names = [int(f.split(".")[0])
                            for f in os.listdir(custom_templates_path)]
    custom_temp_names.sort()
    return Response({"custom_temp_names": custom_temp_names})

# GET - Get the custom template using the template number
@api_view(["GET"])
def getCustomTemplate(request):
    custom_template_path = os.path.join(
        settings.STATIC_ROOT, f"card_templates/Custom/{request.GET.get('number')}.png")
    custom_temp_base64 = encode_image_to_base64(custom_template_path)
    return Response({"custom_temp_base64": custom_temp_base64})

########################################################################################################################

# # POST - Generate the blessing card
# #      - Send template type as custom and template number OR template type as default and template language
# @api_view(["POST"])
# def generateBlessingCardAPI(request):
#     username = request.user.username
#     # Update the count of cards generated by the user
#     if ClickCount.objects.filter(username=username).exists():
#         click_count = ClickCount.objects.get(username=username)
#     else:
#         click_count = ClickCount.objects.create(username=username)
#     click_count.count += 1
#     click_count.save()

#     x_center, y_center = editPhoto("uploaded_photo", username)

#     # Load the data from the request body
#     data = json.loads(request.body)

#     # Get the template type (custom/default)
#     template_type = data.get('template_type')
#     if template_type == "custom":
#         custom_template_folder = os.path.join(
#             settings.STATIC_ROOT, "card_templates/Custom")
#         # Get the template number of custom template
#         selected_custom_template = data.get("template_number")
#         template_path = os.path.join(
#             custom_template_folder, f"{selected_custom_template}.png")

#         height = 242
#     elif template_type == "default":
#         # Get the template language
#         selected_template_lang = data.get("template_language")
#         template_folder = os.path.join(
#             settings.STATIC_ROOT, "card_templates")
#         templates = glob.glob(os.path.join(
#             template_folder, f"{selected_template_lang}", "*.png"))
#         template_path = random.choice(templates)

#         height = 242
#     else:
#         return Response({"status": "Incorrect template type!"})

#     # Read the template and resize
#     template = cv2.imread(template_path)
#     template = cv2.resize(template, (640, 480))

#     # Read the photo and preprocess
#     photo_path = os.path.join(
#         settings.STATIC_ROOT, f"uploaded_photo/uploaded_photo_{username}.png")
#     photo = cv2.imread(photo_path, cv2.IMREAD_UNCHANGED)

#     # Get the original width and height
#     h, w = photo.shape[:2]

#     # Get the ratio to find the light coordinates for the resized image
#     x_ratio = x_center/w
#     y_ratio = y_center/h

#     # Get the aspect ratio to resize the image keep the ratio constant
#     aspect_ratio = w/h

#     x = 0
#     while True:
#         # Get the new height and width to be resized to
#         h_new = height
#         w_new = int(height*aspect_ratio)

#         # Get the new coordinates of the light
#         x_center = int(x_ratio*w_new)
#         y_center = int(y_ratio*h_new)

#         # Find the gap from the extreme left to be kept
#         x = 165 - x_center

#         # The gap should be atleast 50
#         if x >= 45:
#             break
#         else:
#             height -= 5
#     y = 446 - (height)
#     photo = cv2.resize(photo, (int(height*aspect_ratio), height))

#     alpha_channel = photo[:, :, 3]
#     alpha_channel = alpha_channel / 255.0
#     # alpha_mask = cv2.merge([alpha_channel, alpha_channel, alpha_channel])
#     alpha_mask = np.stack([alpha_channel] * 3, axis=-1)
#     photo = photo[:, :, :3]

#     # Perform the overlay process
#     x_end = x + photo.shape[1]
#     y_end = y + photo.shape[0]
#     roi = template[y:y_end, x:x_end]
#     blended_roi = (photo * alpha_mask) + (roi * (1 - alpha_mask))
#     template[y:y_end, x:x_end] = blended_roi
#     # Save the blessing card
#     card_output_path = os.path.join(
#         settings.STATIC_ROOT, f"blessing_card/blessing_card_{username}.png")
#     # cv2.imwrite(card_output_path, template, [cv2.IMWRITE_JPEG_QUALITY, 95])
#     cv2.imwrite(card_output_path, template)
#     return Response({"status": "Blessing Card successfully generated!"})

########################################################################################################################

# POST - Generate the blessing card
#      - Send template type as custom and template number OR template type as default and template language
@api_view(["POST"])
def generateBlessingCardAPI(request):
    username = request.user.username
    # Update the count of cards generated by the user
    if ClickCount.objects.filter(username=username).exists():
        click_count = ClickCount.objects.get(username=username)
    else:
        click_count = ClickCount.objects.create(username=username)
    click_count.count += 1
    click_count.save()

    x_center, y_center = editPhoto("uploaded_photo", username)

    # Load the data from the request body
    data = json.loads(request.body)

    # Get the template type (custom/default)
    template_type = data.get('template_type')
    if template_type == "custom":
        custom_template_folder = os.path.join(
            settings.STATIC_ROOT, "card_templates/Custom")
        # Get the template number of custom template
        selected_custom_template = data.get("template_number")
        template_path = os.path.join(
            custom_template_folder, f"{selected_custom_template}.png")

        height = 863.6375
    elif template_type == "default":
        # Get the template language
        selected_template_lang = data.get("template_language")
        template_folder = os.path.join(
            settings.STATIC_ROOT, "card_templates")
        templates = glob.glob(os.path.join(
            template_folder, f"{selected_template_lang}", "*.png"))
        template_path = random.choice(templates)

        height = 863.6375
    else:
        return Response({"status": "Incorrect template type!"})

    # Read the template and resize
    template = cv2.imread(template_path)

    # Read the photo and preprocess
    photo_path = os.path.join(
        settings.STATIC_ROOT, f"uploaded_photo/uploaded_photo_{username}.png")
    photo = cv2.imread(photo_path, cv2.IMREAD_UNCHANGED)

    # Get the original width and height
    h, w = photo.shape[:2]

    # Get the ratio to find the light coordinates for the resized image
    x_ratio = x_center/w
    y_ratio = y_center/h

    # Get the aspect ratio to resize the image keep the ratio constant
    aspect_ratio = w/h

    x = 0
    while True:
        # Get the new height and width to be resized to
        h_new = height
        w_new = int(height*aspect_ratio)

        # Get the new coordinates of the light
        x_center = int(x_ratio*w_new)
        y_center = int(y_ratio*h_new)

        # Find the gap from the extreme left to be kept
        x = 593.7421875 - x_center

        # The gap should be atleast 50
        if x >= 162:
            break
        else:
            height -= 5
    y = 1591.6625 - (height)
    photo = cv2.resize(photo, (int(height*aspect_ratio), int(height))) 

    alpha_channel = photo[:, :, 3]
    alpha_channel = alpha_channel / 255.0
    alpha_mask = np.stack([alpha_channel] * 3, axis=-1)
    photo = photo[:, :, :3]

    # Perform the overlay process
    x = int(x)
    y = int(y)
    x_end = x + photo.shape[1]
    y_end = y + photo.shape[0]
    roi = template[y:y_end, x:x_end]
    blended_roi = (photo * alpha_mask) + (roi * (1 - alpha_mask))
    template[y:y_end, x:x_end] = blended_roi
    # Save the blessing card
    card_output_path = os.path.join(settings.STATIC_ROOT, f"blessing_card/blessing_card_{username}.png")
    cv2.imwrite(card_output_path, template)
    return Response({"status": "Blessing Card successfully generated!"})

########################################################################################################################

# POST - Send the base64 photo data to store the customized blessing card
@api_view(["POST"])
def saveCustomBlessingCardAPI(request):
    username = request.user.username
    try:
        data = json.loads(request.body)
        blessing_card_base64 = data.get("blessing_card_base64")
        blessing_card_path = os.path.join(settings.STATIC_ROOT, f"blessing_card/blessing_card_{username}.png")
        decode_base64_to_image(blessing_card_base64, blessing_card_path)
        return Response({"status": "Customized Blessing Card saved successfully!"})
    except:
        return Response({"status": "Error saving the Customized Blessing Card"})

# GET - Get the recently generated blessing card
@api_view(["GET"])
def getBlessingCardAPI(request):
    username = request.user.username
    try:
        blessing_card_path = os.path.join(
            settings.STATIC_ROOT, f"blessing_card/blessing_card_{username}.png")
        blessing_card_base64 = encode_image_to_base64(blessing_card_path)
        # clearImages(username)
        return Response({"blessing_card_base64": blessing_card_base64})
    except:
        return Response({"blessing_card_base64": ""})

# POST - Send email data and send the blessing card via email
@api_view(["POST"])
def sendEmailAPI(request):
    try:
        data = json.loads(request.body)
        recipient_email = data.get("rec_email")
        subject = data.get("rec_subject")
        body = data.get("rec_body")
        image_data_base64 = data.get("image_base64")
        image_data = base64.b64decode(image_data_base64)

        # Create the email message
        email = EmailMessage(
            subject,
            body,
            settings.DEFAULT_FROM_EMAIL,
            [recipient_email],
        )
        # Attach the card to the email
        email.attach("blessing_card.jpg", image_data, "image/png")
        # Send the email
        email.send()
        return Response({"message": "Mail sent!"})
    except:
        return Response({"message": "Error sending mail!"})

# GET - Save the blessing card and create a link to access it
@api_view(["POST"])
def getURLAPI(request):
    username = request.user.username
    data = request.data
    image_base64 = data.get("image_base64")

    # Decode base64 string to bytes
    image_data = base64.b64decode(image_base64)

    # Generate a new file name
    file_name, file_extension = os.path.splitext(
        f"blessing_card_{username}.jpg")
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    new_file_name = f"{file_name}_{timestamp}{file_extension}"

    # Destination path where the image will be stored
    destination_path = os.path.join(
        settings.STATIC_ROOT, "card_storage", new_file_name)

    # Save the decoded image data to the destination path
    with open(destination_path, "wb") as f:
        f.write(image_data)

    # Generate the URL for the image (This will be shared on WhatsApp)
    token = secrets.token_hex(16)
    image_url = "https://www.brahmakumarisblessingcard.com" + f"/card/{token}"

    # Map the card path with the random token generated
    obj = TokenPathMapping(image_path=os.path.join(
        settings.STATIC_ROOT, f"card_storage/{new_file_name}"), token=token)
    obj.save()
    return Response({"blessing_card_url": image_url})

# Resolves the image path from the token value when some opens the blessing card link
# and displays the image on their browser
@api_view(["GET"])
def getCard(request, token):
    try:
        obj = TokenPathMapping.objects.get(token=token)
        image_path = obj.image_path
        base_64_image = encode_image_to_base64(os.path.join(settings.STATIC_ROOT, f"{image_path}"))
        return Response({"base_64_image": base_64_image})
    except TokenPathMapping.DoesNotExist:
        return Response({'error_message': 'Image not found'})