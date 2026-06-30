from . import views
from django.urls import path
app_name = 'core'

urlpatterns = [

    path('postecomptable/', views.postcomptabble_list_view, name='postecomptable_list'),
    path('postecomptable/create/', views.PosteComptableCreateView.as_view(), name='create_postecomptable'),
    path('postecomptable/<pk>/delete/', views.PosteComptableDeleteView.as_view(), name='delete_postecomptable'),
    path('postecomptable/<pk>/update/', views.PosteComptableUpdateView.as_view(), name='update_postecomptable'),

    path('tgs/', views.tg_list_view, name='tg_list'),
    path('tg/create/', views.TGCreateView.as_view(), name='create_tg'),

    path('rgt/create/', views.RGTCreateView.as_view(), name='create_rgt'),
    path('acgp/create/', views.ACGPCreateView.as_view(), name='create_acgp'),
    path('tpr/create/', views.TPRCreateView.as_view(), name='create_tpr'),
    path('pgt/create/', views.PGTCreateView.as_view(), name='create_pgt'),


    path('dcp/', views.dcp_list_view, name='dcp_list'),
    path('dcp/create/', views.DCPCreateView.as_view(), name='create_dcp'),
    #path('dcp/<pk>/delete/', views.DCPDeleteView.as_view(), name='delete_dcp'),
    path('dcp/<pk>/update/', views.DCPUpdateView.as_view(), name='update_dcp'),

    path('agentdcps/', views.agent_dcp_list_view, name='profiledcp_list'),
    path('agentdcp/create/', views.ProfileDCPCreateView.as_view(), name='create_profiledcp'),
    path('agentdcp/<pk>/delete/', views.ProfileDCPDeleteView.as_view(), name='delete_profiledcp'),
    path('agentdcp/<pk>/update/', views.ProfileDCPUpdateView.as_view(), name='update_profiledcp'),




    path('agentpcs/', views.agent_pc_list_view, name='profilepc_list'),
    path('agentpc/create/', views.ProfilePCCreateView.as_view(), name='create_profilepc'),
    path('agentpc/<pk>/delete/', views.ProfilePCDeleteView.as_view(), name='delete_profilepc'),
    path('agentpc/<pk>/update/', views.ProfilePCUpdateView.as_view(), name='update_profilepc'),

    path('affectations/', views.affection_list_view, name='affectation_list'),
    path('affectation/create/', views.AffectationAgentCreateView.as_view(), name='create_affectation'),
    path('affectation/<pk>/update/', views.AffectationAgentUpdateView.as_view(), name='update_affectation'),
    path('affectation/<pk>/delete/', views.AffectationAgentDeleteView.as_view(), name='delete_affectation'),
    path('dashposte/<poste_id>/', views.dash_postcomptable_view, name='dash_postcomptable_view'),

    path('secteurs/', views.secteur_list_view, name='secteur_list'),
    path('secteur/create/', views.SecteurCreateView.as_view(), name='create_secteur'),
    path('secteur/<pk>/delete/', views.SecteurDeleteView.as_view(), name='delete_secteur'),
    path('secteur/<pk>/update/', views.SecteurUpdateView.as_view(), name='update_secteur'),

    path('ministeres/', views.ministere_list_view, name='ministere_list'),
    path('ministere/create/', views.MinistereCreateView.as_view(), name='create_ministere'),
    path('ministere/<pk>/delete/', views.MinistereDeleteView.as_view(), name='delete_ministere'),
    path('ministere/<pk>/update/', views.MinistereUpdateView.as_view(), name='update_ministere'),

    path('codeservices/', views.codeservice_list_view, name='codeservice_list'),
    path('codeservice/create/', views.CodeServiceCreateView.as_view(), name='create_codeservice'),
    path('codeservice/<pk>/delete/', views.CodeServiceDeleteView.as_view(), name='delete_codeservice'),
    path('codeservice/<pk>/update/', views.CodeServiceUpdateView.as_view(), name='update_codeservice'),


    path('directions/', views.direction_list_view, name='direction_list'),
    path('direction/create/', views.DirectionCreateView.as_view(), name='create_direction'),
    path('direction/<pk>/delete/', views.DirectionDeleteView.as_view(), name='delete_direction'),
    path('direction/<pk>/update/', views.DirectionUpdateView.as_view(), name='update_direction'),


    path('loaddirections/', views.load_directions_by_ministere, name='load_directions_by_ministere'),
    path('loadstructures/', views.load_structure_by_ministere, name='load_structure_by_ministere'),




    path('groups/', views.list_groups_view, name='group_list'),
    path('group/create/', views.GroupCreateView.as_view(), name='create_group'),
    path('group/<pk>/delete/', views.GroupDeleteView.as_view(), name='delete_group'),
    path('group/<pk>/update/', views.GroupUpdateView.as_view(), name='update_group'),
    path('dashtg/', views.dash_tg_view, name='dash_tg_view'),
    path('olddashtg/', views.dash_tg_old_view, name='dash_tg_old_view'),

    path('dashds/', views.dash_ds_view, name='dash_ds_view'),

    path('structure/', views.structure_list_view, name='structure_list'),
    path('structure/create/', views.StructureCreateView.as_view(), name='create_structure'),
    path('structure/<pk>/delete/', views.StructureDeleteView.as_view(), name='delete_structure'),
    path('structure/<pk>/update/', views.StructureUpdateView.as_view(), name='update_structure'),
    path('linkstructure/', views.link_compte_to_structure, name='link_compte_to_structure'),


    path('maintenance/', views.maintenance, name='maintenance'),

    path('configurationotp/', views.configurationotp_list_view, name='configurationotp_list'),
    path('configurationotp/create/', views.ConfigurationOTPCreateView.as_view(), name='create_configurationotp'),
    path('configurationotp/<pk>/delete/', views.ConfigurationOTPDeleteView.as_view(), name='delete_configurationotp'),
    path('configurationotp/<pk>/update/', views.ConfigurationOTPUpdateView.as_view(), name='update_configurationotp'),



]