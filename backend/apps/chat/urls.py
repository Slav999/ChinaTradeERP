from django.urls import path
from .views import AttachmentView, ClearView, ConversationDetailView, ConversationsView, EmployeesView, MessagesView, ReadView, ReferencesView
from .features import LeaveView, MessageDetailView, PinView, PreferencesView, ReactionView, RelatedView, StorageView, TransferView
from .read_status import ReadStatusView

urlpatterns = [
    path('employees/', EmployeesView.as_view()),
    path('conversations/', ConversationsView.as_view()),
    path('references/', ReferencesView.as_view()),
    path('related/', RelatedView.as_view()),
    path('storage/', StorageView.as_view()),
    path('conversations/<int:pk>/preferences/', PreferencesView.as_view()),
    path('conversations/<int:pk>/transfer/', TransferView.as_view()),
    path('conversations/<int:pk>/leave/', LeaveView.as_view()),
    path('conversations/<int:pk>/', ConversationDetailView.as_view()),
    path('conversations/<int:pk>/clear/', ClearView.as_view()),
    path('conversations/<int:pk>/attachments/<int:attachment_id>/', AttachmentView.as_view()),
    path('conversations/<int:pk>/messages/', MessagesView.as_view()),
    path('conversations/<int:pk>/messages/<int:message_id>/', MessageDetailView.as_view()),
    path('conversations/<int:pk>/messages/<int:message_id>/reaction/', ReactionView.as_view()),
    path('conversations/<int:pk>/messages/<int:message_id>/pin/', PinView.as_view()),
    path('conversations/<int:pk>/read/', ReadView.as_view()),
    path('conversations/<int:pk>/read-status/', ReadStatusView.as_view()),
]
