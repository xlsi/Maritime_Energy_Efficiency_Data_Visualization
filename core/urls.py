from django.urls import path
from django.contrib import admin

import app.views

admin.autodiscover()


urlpatterns = [
    path('', app.views.index, name='index'),
    path('db/', app.views.db, name='db'),
    path('emissions/', app.views.emissions, name='emissions'),
    path('emissions/<int:page>', app.views.emissions, name='emissions'),
    path('emissions/imo/', app.views.emission_detail, name='emission_detail'),
    path('emissions/imo/<int:imo>', app.views.emission_detail, name='emission_detail'),
    path('admin/', admin.site.urls),
    path('aggregation/', app.views.aggregation, name='aggregation'),
    path('visual/', app.views.visual, name='visual'),
    path('explore/', app.views.explore, name='explore'),
    path('explore/<int:page>', app.views.explore, name='explore'),
    path('explore/imo/<int:imo>', app.views.explore_detail, name='explore_detail'),
    path('explore/ship_name/<str:ship_name>', app.views.explore_ship_name, name='explore_ship_name'),
    path('total_co2_emission/', app.views.total_co2_emission, name='total_co2_emission')
]
