from . import views
from django.urls import path
app_name = 'cddaccount'

urlpatterns = [
    path('newcomptedepots/', views.new_comptedepot_list_view, name='new_comptedepot_list'),
	path('comptedepots/', views.comptedepot_list_view, name='comptedepot_list'),
	path('secretecdd/', views.secrete_comptedepot_list_view, name='secrete_comptedepot_list'),
    path('comptedepots/releves', views.comptedepot_list_view, name='comptedepot_releve'),
	path('ajax/compteinfos/', views.load_compte_infos, name='load_compte_infos'),
	path('ajax/gencddacc/', views.ajax_generate_account_number, name='ajax_generate_account_number'),
    path('ajax/getsoldecddacc/', views.ajax_getsolde_cdd, name='ajax_getsolde_cdd'),


    path('comptedepot/create/', views.CompteDepotCreateView.as_view(), name='create_comptedepot'),
    path('comptedepot/<pk>/delete/', views.CompteDepotDeleteView.as_view(), name='delete_comptedepot'),
    path('comptedepot/<pk>/update/', views.CompteDepoteUpdateView.as_view(), name='update_comptedepot'),
	path('comptedepot/<pk>/dash/', views.comptedepot_dash_view, name='comptedepot_dash_view'),

	path('comptedepot/<id>/validate/', views.create_validationcompte, name='create_validationcompte'),
	#path('comptedepot/<str:reference>/<date:startdate>/<date:enddate>/releve/', views.releve_compte_view, name='releve_compte_view'),

	path('comptedepot/<str:reference>/<date:startdate>/<date:enddate>/<int:gestion>/<int:inst>/releve/', views.releve_compte_view, name='releve_compte_view'),
    path('comptedepot/pdf/<str:reference>/<date:startdate>/<date:enddate>/<int:gestion>/<int:inst>/releve/', views.releve_compte_pdf_view, name='releve_compte_pdf_view'),

	path('comptedepot/<str:reference>/genreleve/', views.genere_releve_compte_view, name='genere_releve_compte'),

	path('comptedepot/<id>/activer/', views.activer_comptedepot, name='activer_comptedepot'),


	path('banks/', views.bank_list_view, name='bank_list'),
	path('bank/create/', views.BankCreateView.as_view(), name='create_bank'),
	path('bank/<pk>/delete/', views.BankDeleteView.as_view(), name='delete_bank'),
	path('bank/<pk>/update/', views.BankUpdateView.as_view(), name='update_bank'),


	path('codeagences/', views.codeagence_list_view, name='codeagence_list'),
	path('codeagence/create/', views.CodeAgenceCreateView.as_view(), name='create_codeagence'),
	path('codeagence/<pk>/delete/', views.CodeAgenceDeleteView.as_view(), name='delete_codeagence'),
	path('codeagence/<pk>/update/', views.CodeAgenceUpdateView.as_view(), name='update_codeagence'),

	path('gerantcd/create/', views.StartGerantCDCreateView.as_view(), name='create_gerantcd'),

	path('gerantcd/<pk>/complete/', views.complete_gerantcd_data, name='complete_gerant'),


	path('gerantcds/', views.gerantcd_list_view, name='gerantcd_list'),

	path('gerantcd/<pk>/delete/', views.GerantCDDeleteView.as_view(), name='delete_gerantcd'),
	path('gerantcd/<pk>/update/', views.GerantCDUpdateView.as_view(), name='update_gerantcd'),


	path('gerantcd/<str:matricule>/dash/', views.gerantcd_profile_view, name='gerantcd_profile'),
	path('gerantcd/<str:matricule>/simpledash/', views.simple_gerantcd_profile_view, name='simple_gerantcd_profile'),

	path('gerantcd/<str:matricule>/validation/', views.validate_gerantcd_data, name='validate_gerantcd_data'),

	path('gerantcd/bordereaux/', views.all_bord_gerant_view, name='all_bord_gerant_view'),
	path('gerantcd/edit/bordereau', views.edit_bordereau_op, name='bordereau_op'),


	#path('gestioncomptedepots/', views.gestion_ccompte_depot_view, name='gestioncomptedepot_list'),


	path('agentsaisiecd/create/', views.StartAgentSaisieCDCreateView.as_view(), name='create_agentsaisiecd'),

	path('agentsaisiecd/<pk>/complete/', views.complete_agentsaisiecd_data, name='complete_agentsaisiecd'),




	path('agentsaisiecds/', views.agentsaisie_cd_list_view, name='agentsaisiecd_list'),
	path('agentsaisiecd/<pk>/delete/', views.AgentSaisieCDDeleteView.as_view(), name='delete_agentsaisiecd'),
	path('agentsaisiecd/<pk>/update/', views.AgentSaisieCDUpdateView.as_view(), name='update_agentsaisiecd'),
	path('agentsaisiecd/<str:matricule>/validation/', views.validate_agentsaisiecd_data, name='validate_agentsaisiecd_data'),
	path('agentsaisiecd/<str:matricule>/dash/', views.agentsaisiecd_profile_view, name='agentsaisiecd_profile_view'),
	path('agentsaisiecd/<str:matricule>/sendsms/', views.send_sms, name='send_sms'),


	path('gestioncomptedepots/', views.gestioncomptedepot_list_view, name='gestioncomptedepot_list'),
	path('gestioncomptedepot/create/', views.GestionCompteDepotCreateView.as_view(), name='create_gestioncomptedepot'),

	path('gestioncomptedepot/<pk>/delete/', views.GestionCompteDepotDeleteView.as_view(), name='delete_gestioncomptedepot'),
	path('gestioncomptedepot/<pk>/update/', views.GestionCompteDepotUpdateView.as_view(), name='update_gestioncomptedepot'),

	path('ordrepayment/create/', views.OrdrePaymentDefaultCreateView.as_view(), name='create_ordrepayment_default'),
	path('ordrepayment/<pk>/create/', views.OrdrePaymentCreateView.as_view(), name='create_ordrepayment'),
	path('ordrepayments/', views.ordrepayment_list_view, name='ordrepayment_list'),
    path('ordrepayment/seesolde/', views.seesolde_op_view, name='seesolde_op_view'),

	path('opvirements/', views.opvirements_list_view, name='opvirements_list'),
	path('opcheques/', views.opcheques_list_view, name='opcheques_list'),


	path('ordrepayment/<pk>/delete/', views.OrdrePaymentDeleteView.as_view(), name='delete_ordrepayment'),
	path('ordrepayment/<pk>/update/', views.OrdrePaymentUpdateView.as_view(), name='update_ordrepayment'),

	path('ordrepayment/<pk>/pmupdate/', views.OrdrePaymentUpdatePaymentView.as_view(), name='update_pm_ordrepayment'),

	path('ordrepayment/<pk>/priseencharge/', views.prise_en_charge_view, name='prise_en_charge_view'),
	path('ordrepayment/<str:reference>/validate/', views.validate_ordre_payment_view, name='validate_ordre_payment'),
	path('ordrepayment/<str:reference>/accepter/', views.accepter_ordre_payment_view, name='accepter_ordre_payment'),
	path('ordrepayment/<str:reference>/template/', views.temlate_op_view, name='temlate_op_view'),
    path('ordrepayment/<str:reference>/template_pdf/', views.temlate_op_pdf_view, name='temlate_op_pdf_view'),

	path('demandeop/<str:reference>/template/', views.temlate_demandeop_view, name='temlate_demandeop_view'),


    

	path('ordrepayment/<str:reference>/visa/', views.viser_ordre_payement_view, name='viser_ordre_payement'),

	path('ordrepayment/<str:reference>/modalvisa/', views.modal_viser_ordre_payement_view, name='modal_viser_ordre_payement'),

	path('ordrepayment/<str:reference>/details/', views.detail_ordre_payement_view, name='detail_ordre_payement'),
    path('ordrepayment/<str:reference>/pay/', views.maketrx_ordre_payement_view, name='maketrx_ordre_payement'),
	path('ordrepayment/<str:reference>/delivredcheck/', views.receptionner_cheque_view, name='receptionner_cheque'),

	path('ordrepayment/<str:reference>/cancel/', views.annulation_op_view, name='annulation_op'),
	path('ordrepayment/<str:reference>/reject/', views.reject_op_view, name='reject_op'),
	path('ordrepayment/generate_vrm_template/', views.generate_template_vrm, name='generate_template_vrm'),

	path('trx/<str:reference>/recu/', views.recu_payement_view, name='recu_payement'),


	path('depositaires/', views.deposotaires_list_view, name='depositaire_list'),
	path('depositaire/create/', views.DepositaireCreateView.as_view(), name='create_depositaire'),
	path('depositaire/<pk>/delete/', views.DepositaireDeleteView.as_view(), name='delete_depositaire'),
	path('depositaire/<pk>/update/', views.DepositaireUpdateView.as_view(), name='update_depositaire'),

	path('natures/', views.nature_list_view, name='nature_list'),
	path('nature/create/', views.NatureCreateView.as_view(), name='create_nature'),
	path('nature/<pk>/delete/', views.NatureDeleteView.as_view(), name='delete_nature'),
	path('nature/<pk>/update/', views.NatureUpdateView.as_view(), name='update_nature'),


	path('sousnatures/', views.sousnature_list_view, name='sousnature_list'),
	path('sousnature/create/', views.SousNatureCreateView.as_view(), name='create_sousnature'),
	path('sousnature/<pk>/delete/', views.SousNatureDeleteView.as_view(), name='delete_sousnature'),
	path('sousnature/<pk>/update/', views.SousNatureUpdateView.as_view(), name='update_sousnature'),
	path('loadsousnnatures/', views.load_sousnnature_by_nature, name='load_sousnnature_by_nature'),

	path('priseencharge/<pk>/delete/', views.PrisEnchageOrdrePaymentDeleteView.as_view(), name='delete_priseencharge'),
	path('priseencharge/<pk>/update/', views.PrisEnchageOrdrePaymentUpdateView.as_view(), name='update_priseencharge'),

	path('projets/', views.projets_list_view, name='projet_list'),
	path('projet/create/', views.ProjetCreateView.as_view(), name='create_projet'),
	path('projet/<pk>/delete/', views.ProjetDeleteView.as_view(), name='delete_projet'),
	path('projet/<pk>/update/', views.ProjetUpdateView.as_view(), name='update_projet'),

	path('projet/<pk>/validerbf/', views.valider_projet_bf_view, name='valider_projet_bf'),
	path('projet/<pk>/demanderbf/', views.demander_bf_projet_view, name='demander_bf_projet'),
	path('projet/<pk>/details/', views.details_projet_bf_view, name='details_projet_bf'),

	path('avisdedebits/', views.avisdedebit_list_view, name='avisdedebit_list'),
	path('avisdedebit/create/', views.AvisDeDebitCreateView.as_view(), name='create_avisdedebit'),
	path('avisdedebit/<pk>/delete/', views.AvisDeDebitDeleteView.as_view(), name='delete_avisdedebit'),
	path('avisdedebit/<pk>/update/', views.AvisDeDebitUpdateView.as_view(), name='update_avisdedebit'),
	path('avisdedebit/<str:reference>/template/', views.temlate_avisdebit_view_pdf, name='template_avisdebit_pdf'),

	path('avisdecredits/', views.avisdecredit_list_view, name='avisdecredit_list'),
	path('avisdecredit/create/', views.AvisDeCreditCreateView.as_view(), name='create_avisdecredit'),
	path('avisdecredit/<pk>/delete/', views.AvisDeCreditDeleteView.as_view(), name='delete_avisdecredit'),
	path('avisdecredit/<pk>/update/', views.AvisDeCreditUpdateView.as_view(), name='update_avisdecredit'),
	path('avisdecredit/<str:reference>/template/', views.template_aviscredit_view_pdf, name='template_aviscredit'),

	path('anneecomptables/', views.anneecomptable_list_view, name='anneecomptable_list'),
    path('anneecomptable/<id>/basculer/', views.basculer_gestion_view, name='bascule_anneecomptable'),

	path('anneecomptable/create/', views.AnneeComptableCreateView.as_view(), name='create_anneecomptable'),
	path('anneecomptable/<pk>/delete/', views.AnneeComptableDeleteView.as_view(), name='delete_anneecomptable'),
	path('anneecomptable/<pk>/update/', views.AnneeComptableUpdateView.as_view(), name='update_anneecomptable'),


	path('blocagefonds/', views.blocagefond_list_view, name='blocagefond_list'),
	path('blocagefond/create/', views.BlocageFondCreateView.as_view(), name='create_blocagefond'),
	path('blocagefond/<pk>/delete/', views.BlocageFondDeleteView.as_view(), name='delete_blocagefond'),
	path('blocagefond/<pk>/update/', views.BlocageFondUpdateView.as_view(), name='update_blocagefond'),

	path('blocagefond/<pk>/details/', views.details_blocagefond_view, name='details_blocagefond'),
	path('switchcontext/', views.switch_contexte, name='switch_contexte'),
	path('blocagefond/<str:reference>/annuler/', views.deblocage_fond_view, name='deblocage_fond_view'),

	path('annulationblocagefonds/', views.annulationblocagefond_list_view, name='annulationblocagefond_list'),



	path('blocagefond/<str:reference>/opcreate/', views.OrdrePaymentByBFCreateView.as_view(), name='create_op_blocagefond'),
	path('op/<pk>/cancelvisa/', views.annuler_visa_view, name='annuler_visa_view'),





	path('ordrespop/bulkall/', views.bulk_action, name='bulk_action'),
	path('ordrespop/bulkretrait/', views.bulk_retrait_cheque_ops, name='bulk_retrait_cheque_ops'),
	path('ordrespop/bulkconfirmotprecq/<str:reference>/<str:matricule>/', views.bulk_otp_confirm_retrait_cheque, name='bulk_otp_confirm_retrait_cheque'),

	path('ordrespop/bulkdelop/', views.bulk_delete_ops, name='bulk_delete_ops'),
	path('ordrespop/bulkotp/<str:reference>/<str:matricule>/', views.bulk_otp_confirm_op, name='bulk_otp_confirm_op'),
	path('blocagefond/<str:reference>/approuveran/', views.approuver_deblocage_fond_view, name='approuver_deblocage_fond'),
	path('blocagefond/<str:reference>/template/', views.temlate_bf_view, name='temlate_bf'),


	path('opvirements/news/', views.nouveaux_virements_list_view, name='nouveaux_virements_list'),
	path('opvirements/valides/', views.valides_virements_list_view, name='valides_virements_list'),
	path('opvirements/acceptes/', views.accepter_virements_list_view, name='accepter_virements_list'),
	path('opvirements/prisecharges/', views.priseencharge_virements_list_view, name='priseencharge_virements_list'),
	path('opvirements/vises/', views.visa_virements_list_view, name='visa_virements_list'),


	path('opcheques/news/', views.nouveaux_opcheques_list_view, name='nouveaux_opcheques_list'),
	path('opcheques/valides/', views.valides_opcheques_list_view, name='valides_opcheques_list'),
	path('opcheques/acceptes/', views.accepter_opcheques_list_view, name='accepter_opcheques_list'),
	path('opcheques/prisecharges/', views.priseencharge_opcheques_list_view, name='priseencharge_opcheques_list'),
	path('opcheques/vises/', views.visa_opcheques_list_view, name='visa_opcheques_list'),
    path('deja/vises/', views.op_dejavises_list_view, name='op_dejavises_list_view'),
	path('virementdetails/', views.details_vire_list_view, name='details_vire_list_view'),
	path('mblvirementdetails/', views.mobile_details_vire_list_view, name='mobile_details_vire_list_view'),






	path('inoice_viewr/', views.inoice_view, name='inoice_view'),

	path('reports/', views.report_list_view, name='reportgestion_list'),
    path('report/create/', views.ReportCreateView.as_view(), name='create_reportgestion'),
    path('report/<pk>/delete/', views.ReportDeleteView.as_view(), name='delete_reportgestion'),
    path('report/<pk>/update/', views.ReportUpdateView.as_view(), name='update_reportgestion'),

	path('login/', views.CustomLoginView.as_view(), name='login'),
	path('selectcdd/', views.select_cddaccount_for_work_view, name='select_cddaccount_for_work'),


	path('virementmasse/create/', views.VirementMasseCreateView.as_view(), name='create_virementmasse_default'),

	path('virmasse/news/', views.nouveaux_virmasse_list_view, name='nouveaux_virmasse_list'),
	path('virmasse/valides/', views.valides_virmasse_list_view, name='valides_virmasse_list'),
	path('virmasse/acceptes/', views.accepter_virmasse_list_view, name='accepter_virmasse_list'),
	path('virmasse/prisecharges/', views.priseencharge_virmasse_list_view, name='priseencharge_virmasse_list'),
	path('virmasse/vises/', views.visa_virmasse_list_view, name='visa_virmasse_list'),





	path('operations/news/', views.nouveaux_op_list_view, name='nouveaux_op_list'),
	path('operations/valides/', views.valides_op_list_view, name='valides_op_list'),
	path('operations/acceptes/', views.accepter_op_list_view, name='accepter_op_list'),
	path('operations/prisecharges/', views.priseencharge_op_list_view, name='priseencharge_op_list'),


	path('operations/vises/', views.visa_op_list_view, name='visa_op_list'),

	path('operations/consultations/', views.consulter_op_list_view, name='consulter_op_list'),

	path('test_view/', views.test_view, name='test_view'),
	path('chargementfichier/', views.chargement_view, name='chargement_view'),

	path('balance/view/', views.balance_view, name='balance_view'),
	path('balance/generate/', views.genere_balance_view, name='genere_balance_view'),


	path('balanceconso/view/', views.balanceconso_view, name='balanceconso_view'),
	path('balanceconso/generate/', views.genere_balanceconso_view, name='genere_balanceconso_view'),


	path('repport/op/vise/', views.repport_op_vise_view, name='repport_op_vise_view'),
	path('repport/generate/', views.genere_repport_opvise_view, name='genere_repport_opvise_view'),


	path('repport/op/chequepartiellementvise/', views.rapport_cheques_partiellement_visees_view, name='rapport_cheques_partiellement_visees_view'),
	path('repport/op/chequepartiellementvise/generate/', views.show_genere_rapport_cheques_partiellement_visees_view, name='show_genere_rapport_cheques_partiellement_visees_view'),


	path('repport/avis/', views.avisdedebit_report_view, name='avisdedebit_report_view'),
	path('repport/generate/avis/', views.genere_repport_avisdebit_view, name='genere_repport_avisdebit_view'),
    
    

	path('repport/op/vise/moyenpaiement/', views.repport_op_paye_view, name='repport_op_paye_view'),
	path('repport/generate/moyenpaiement/', views.genere_repport_op_paye_view, name='genere_repport_op_paye_view'),

	path('disponible/list/', views.disponible_situation_view, name='disponible_situation_view'),
	#path('disponible2/list/', views.disponible_situation_view_new, name='disponible_situation_view_new'),

	path('disponible/generate/', views.show_disponible_form_view, name='show_disponible_form_view'),


    path('sitopnat/list/', views.op_by_nature_view, name='op_by_nature_view'),
	path('sitopnat/generate/', views.show_opbynature_form_view, name='show_opbynature_form_view'),

	path('gerenat/currentrlv/', views.gerant_curent_releve, name='gerant_curent_releve'),
	path('gerenat/currentrdlv/', views.gerant_curent_detaillereleve, name='gerant_curent_detaillereleve'),


	path('sitophs/hs/', views.situation_op_hs_view, name='situation_op_hs_view'),
	path('sitops/s/', views.situation_op_s_view, name='situation_op_s_view'),
	path('sitopall/all/', views.situation_op_all_view, name='situation_op_all_view'),
	path('sitopall/generate/', views.show_situation_cdd_form_view, name='show_situation_cdd_form_view'),
    path('check-task/<str:task_id>/', views.check_task_status, name='check_task_status'),
    path('sitops/s/generate/', views.show_sit_instance_op_s_form_view, name='show_sit_instance_op_s_form_view'),
    path('sitophs/hs/generate/', views.show_sit_instance_op_hs_form_view, name='show_sit_instance_op_hs_form_view'),

	path('sitconssolide/cp/', views.situation_consolde_view, name='situation_consolde_view'),
	path('comptedepot/<str:reference>/genrelevedetaille/', views.genere_relevedetaille_compte_view, name='genere_relevedetaille_compte_view'),

	path('comptedepot/<str:reference>/<date:startdate>/<date:enddate>/<int:gestion>/<int:inst>/detaillerv/', views.releve_compte_detaille_view, name='releve_compte_detaille_view'),

	path('mandataires/', views.mandataires_list_view, name='mandataire_list'),
	path('mandataire/create/', views.MandataireCreateView.as_view(), name='create_mandataire'),
	path('mandataire/<pk>/delete/', views.MandataireDeleteView.as_view(), name='delete_mandataire'),
	path('mandataire/<pk>/update/', views.MandataireUpdateView.as_view(), name='update_mandataire'),

	path('verify/<str:reference>/takenCheque/', views.send_otp_to_receptionnaire, name='takecheque'),

	path('report/aviscredit/compte/', views.report_aviscredit_compte_view, name='report_aviscredit_compte_view'),

	path('report/generate/aviscredit/', views.genere_report_aviscredit_view, name='genere_report_aviscredit_view'),

	path('chequeop/<str:reference>/processretrait/', views.send_otp_to_receptionnaire_new, name='send_otp_to_receptionnaire_new'),

	path('ajax/send_cheque_otp/', views.send_otp_sms_for_cheque, name='send_otp_sms_for_cheque'),
	path('ajax/vetify_cheque_otp/', views.verify_otp_sms_for_cheque, name='verify_otp_sms_for_cheque'),
	path('ajax/load_compte_by_poste/', views.load_compte_by_poste, name='load_comptes_by_poste'),

	path('ajax/getcdd_current_gerant/', views.ajax_getcdd_current_gerant, name='ajax_getcdd_current_gerant'),


	path('oppc/<pk>/delete/', views.delete_pc_opwith_validate_status, name='delete_pc_opwith_validate_status'),
	path('verify_iban/', views.verify_iban, name='verify_iban'),
    path('sendsitdispbymail/', views.generate_sitdisponible_in_excel, name='generate_sitdisponible_in_excel'),


    path('ajax/msend_cheque_otp/', views.send_otp_sms_for_multicheque, name='send_otp_sms_for_multicheque'),
	path('ajax/mvetify_cheque_otp/', views.verify_otp_sms_for_multicheque, name='verify_otp_sms_for_multicheque'),

	path('sendopvisebymail/', views.generate_opvise_in_excel, name='generate_opvise_in_excel'),
	path('sendaviscreditbymail/', views.generate_report_aviscredit_in_excel, name='generate_report_aviscredit_in_excel'),
	path('sendavisdebitbymail/', views.generate_report_avisdebit_in_excel, name='generate_report_avisdebit_in_excel'),
	path('callback/<str:token>/trx/',views.process_cbk_data, name='process_cbk_data'),


    path('typecomptetrxs/', views.typecomptetrx_list_view, name='typecomptetrx_list'),
	path('typecomptetrx/create/', views.TypeCompteTrxCreateView.as_view(), name='create_typecomptetrx'),
	path('typecomptetrx/<pk>/delete/', views.TypeCompteTrxDeleteView.as_view(), name='delete_typecomptetrx'),
	path('typecomptetrx/<pk>/update/', views.TypeCompteTrxUpdateView.as_view(), name='update_typecomptetrx'),


    path('comptetrxs/', views.comptetrx_list_view, name='comptetrx_list'),
	path('comptetrx/<pk>/update/', views.CompteTrxUpdateView.as_view(), name='update_comptetrx'),


    path('repport/bf/vise/', views.repport_bf_vise_view, name='repport_bf_vise_view'),
	#path('repport/bf/vise/pdf/', views.repport_op_vise_pdf_view, name='repport_bf_vise_pdf_view'),
	path('repport/bfgenerate/', views.genere_repport_bfvise_view, name='genere_repport_bfvise_view'),



	path('demandeops/', views.demandeop_list_view, name='demandeop_list'),
	path('demandeop/create/', views.DemandeOPCreateView.as_view(), name='create_demandeop'),
	path('demandeop/<pk>/delete/', views.DemandeOPDeleteView.as_view(), name='delete_demandeop'),
	path('demandeop/<pk>/update/', views.DemandeOPUpdateView.as_view(), name='update_demandeop'),

]