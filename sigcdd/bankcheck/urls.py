from . import views
from django.urls import path
app_name = 'bankcheck'

urlpatterns = [


    path('daps/', views.dap_list_view, name='dap_list'),
    path('dap/create/', views.DAPCreateView.as_view(), name='create_dap'),
    path('dap/<pk>/delete/', views.DAPDeleteView.as_view(), name='delete_dap'),
    path('dap/<pk>/update/', views.DAPUpdateView.as_view(), name='update_dap'),

    path('agentdaps/', views.agent_dap_list_view, name='agentdap_list'),
    path('agentdap/create/', views.AgentDAPCreateView.as_view(), name='create_agentdap'),
    path('agentdap/<pk>/delete/', views.AgentDAPDeleteView.as_view(), name='delete_agentdap'),
    path('agentdap/<pk>/update/', views.AgentDAPUpdateView.as_view(), name='update_agentdap'),


    path('typechequiers/', views.typechequier_list_view, name='typechequier_list'),
    path('typechequier/create/', views.TypeChequierCreateView.as_view(), name='create_typechequier'),
    path('typechequier/<pk>/delete/', views.TypeChequierDeleteView.as_view(), name='delete_typechequier'),
    path('typechequier/<pk>/update/', views.TypeChequierUpdateView.as_view(), name='update_typechequier'),
    path('commandechequier/', views.commande_chequier_view, name='commande_chequier_view'),

    path('commandes/', views.commande_list_view, name='commandes_list'),
    path('commandesencours/', views.commandes_encours_list, name='commandes_encours_list'),
    path('commandestraite/', views.commandes_traite_list, name='commandes_traite_list'),
    path('commande/<pk>/delete/', views.CommandeDeleteView.as_view(), name='delete_commande'),
    path('commande/<str:reference>/update/', views.update_commande_chequier_view, name='update_commande'),
    path('commande/<str:reference>/accepter/', views.accepter_commande_chequier_view, name='accepter_commande_chequier'),
    path('commande/<str:reference>/valider/', views.valider_commande_chequier_view, name='valider_commande_chequier'),
    path('commandes/all/', views.edit_all_bordereau, name='valider_all_commande'),
    #path('commande/all/traiter', views.all_bordereau_commande_view, name='commande_traiter'),
    path('commande/<str:reference>/bordereau/', views.bordereau_commande_view, name='bordereau_commande_view'),


    path('chequier/<str:reference>/bordereau/', views.all_bordereau_commande_view, name='commande_traiter'),
    path('bordereaux/', views.bordereau_list_view, name='bordereau_list_view'),





    path('cheques/', views.cheques_list_view, name='cheques_list'),

    path('chequiers/', views.chequier_list_view, name='chequiers_list'),
    path('chequier/<str:reference>/bloquer/', views.bloquer_chequier_view, name='bloquer_chequier'),
    path('chequier/<str:reference>/delivrer/', views.delivrer_chequier_view, name='delivrer_chequier'),

    path('ajax/send_cheque_otp/', views.send_otp_sms_for_chequier, name='send_otp_sms_for_chequier'),
	path('ajax/vetify_cheque_otp/', views.verify_otp_sms_for_chequier, name='verify_otp_sms_for_chequier'),

    path('chequier/<str:reference>/details/', views.details_chequier_view, name='details_chequier'),
    path('chequier/<str:reference>/priseencharge/', views.priseencharge_chequier_view, name='priseencharge_chequier'),
    path('chequiers/bulkprisenecharge/', views.bulk_prise_en_charge, name='bulk_prise_en_charge'),
    path('chequiers/bulkotp/<str:reference>/<str:matricule>/', views.bulk_otp_en_charge, name='bulk_otp_en_charge'),
    path('chequiers/bulklivraisongr/', views.bulk_livraison_gerant, name='bulk_livraison_gerant'),

    path('chequiers/bulkotppc/<str:reference>/<str:matricule>/', views.bulk_otp_en_charge_pc, name='bulk_otp_en_charge_pc'),

    path('chequiers/bulklivraisonpc/', views.bulk_livraison_postecomptable, name='bulk_livraison_postecomptable'),
    path('chequiers/bulkall/', views.bulk_action, name='bulk_action'),


    path('annulationcheques/', views.annulationcheques_list_view, name='annulationcheque_list'),
    path('annulationcheque/create/', views.AnnulationChequeCreateView.as_view(), name='create_annulationcheque'),
    path('annulationcheque/<pk>/delete/', views.AnnulationChequeDeleteView.as_view(), name='delete_annulationcheque'),
    path('annulationcheque/<pk>/update/', views.AnnulationChequeUpdateView.as_view(), name='update_annulationcheque'),
    path('annulationcheque/<str:reference>/accepter/', views.accepter_annulationcheque_view, name='accepter_annulationcheque'),
    path('annulationcheque/<str:reference>/approuver/', views.approuver_annulationcheque_view, name='approuver_annulationcheque'),



    path('miseenoppositions/', views.miseenoppositions_list_view, name='miseenopposition_list'),
    path('miseenopposition/create/', views.MiseEnOppositionCreateView.as_view(), name='create_miseenopposition'),
    path('miseenopposition/<pk>/delete/', views.MiseEnOppositionDeleteView.as_view(), name='delete_miseenopposition'),
    path('miseenopposition/<pk>/update/', views.MiseEnOppositionUpdateView.as_view(), name='update_miseenopposition'),

    path('miseenopposition/<str:reference>/accepter/', views.accepter_miseenopposition_view, name='accepter_miseenopposition'),
    path('miseenopposition/<str:reference>/approuver/', views.approuver_miseenopposition_view, name='approuver_miseenopposition'),


    path('compensecheques/', views.compensecheques_list_view, name='compensecheque_list'),
    path('compensecheque/create/', views.CompenseChequeCreateView.as_view(), name='create_compensecheque'),
    path('compensecheque/<pk>/delete/', views.CompenseChequeDeleteView.as_view(), name='delete_compensecheque'),
    path('compensecheque/<pk>/update/', views.CompenseChequeUpdateView.as_view(), name='update_compensecheque'),

    path('rejetcheques/', views.rejetcheques_list_view, name='rejetcheque_list'),
    path('rejetcheque/create/', views.RejetChequeCreateView.as_view(), name='create_rejetcheque'),
    path('rejetcheque/<pk>/delete/', views.RejetChequeDeleteView.as_view(), name='delete_rejetcheque'),
    path('rejetcheque/<pk>/update/', views.RejetChequeUpdateView.as_view(), name='update_rejetcheque'),
    path('rejetcheque/<str:reference>/accepter/', views.accepter_rejetcheque_view,
         name='accepter_rejetcheque'),

    path('chequescannes/', views.chequescannes_list_view, name='chequescannes_list'),

    path('recepchequiers/', views.recep_chequier_list_view, name='recep_chequiers_list'),
    path('distchequiers/', views.dist_chequier_list_view, name='dist_chequiers_list'),
    path('affchequiers/', views.affecter_chequier_list_view, name='aff_chequiers_list'),

    path('dlvredchequiers/', views.delivred_chequier_list_view, name='delivred_chequier_list'),




    path('comptablematieres/', views.comptablematiere_list_view, name='comptablematiere_list'),
	path('comptablematiere/create/', views.ComptableMatiereCreateView.as_view(), name='create_comptablematiere'),
	path('comptablematiere/<pk>/delete/', views.ComptableMatiereDeleteView.as_view(), name='delete_comptablematiere'),
	path('comptablematiere/<pk>/update/', views.ComptableMatiereUpdateView.as_view(), name='update_comptablematiere'),

    path('ajax/send_agtpc_otp/', views.send_otp_sms_for_agent_pc, name='send_otp_sms_for_agent_pc'),
	path('ajax/vetify_agtpc_otp/', views.verify_otp_sms_for_agent_pc, name='verify_otp_sms_for_agent_pc'),
    path('search_cheque/', views.get_infos_cheque_view, name='get_infos_cheque_view'),




]