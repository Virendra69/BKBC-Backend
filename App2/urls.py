from knox import views as knox_views
from django.urls import path
from .views import *

urlpatterns = [
    path("api/login/", LoginView.as_view(), name='knox_login'),
    path("api/logout/", LogoutView.as_view(), name='knox_logout'),
    path("api/logoutall/", LogoutAllView.as_view(), name='knox_logoutall'),
    path("api/get-total-card-count/", getTotalCardCountAPI),
    path("api/clear-data/", clearData),
    path("api/get-username/", getUsernameAPI),
    path("api/remove-user/", removeUser),
    path("api/upload-photo-page/", uploadPhotoPageAPI),
    path("api/create-user/", createUser),
    path("api/get-user-statistics/", getUserStatistics),
    path("api/save-uploaded-photo/", saveUploadedPhotoAPI),
    path("api/get-default-template-languages/", getDefaultTemplateLanguagesAPI),
    path("api/get-customized-templates-number/", getCustomizedTemplatesNumberAPI),
    path("api/get-custom-template/", getCustomTemplate),
    path("api/generate-blessing-card/", generateBlessingCardAPI),
    path("api/save-custom-blessing-card/", saveCustomBlessingCardAPI),
    path("api/get-blessing-card/", getBlessingCardAPI),
    path("api/send-email/", sendEmailAPI),
    path("api/copy-link/", getURLAPI),

    # View the stored image
    path("api/<str:token>/", getCard),
]