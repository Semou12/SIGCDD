
from django.urls import path,include,re_path
from api.views import  *
from rest_framework import routers
from rest_framework.urlpatterns import format_suffix_patterns


snippet_getcheque = AsterAPIViewSet.as_view({'get': 'getcheque'})





router = routers.SimpleRouter()
router.register(r'aster', AsterAPIViewSet, basename='aster')
#urlpatterns = router.urls
app_name = 'api'
urlpatterns = [
	path('', include(router.urls)),
	path('aster/getcheque/<str:reference>/', snippet_getcheque, name='getcheque'),
]
