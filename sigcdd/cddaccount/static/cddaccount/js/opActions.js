$(function () {

       var  allCheckbox =$('#selectAll');
       $('#selectAll').click(function(e){
          var table= $(e.target).closest('table');
          $('td input:checkbox',table).prop('checked',this.checked);
          submitButton = $("button[type='submit']");
          submitButton.attr("disabled", !allCheckbox.is(":checked"));

       });


          // Create item synchronous
          function createItemSyncModalForm(eltId,createUrl) {
            $("#create-item-op").modalForm({
                formURL: createUrl,
                modalID: "#create-modal"
            });
          }

          createItemSyncModalForm($("#create-item-op"),"{{create_url}}");

            function deleteItemModalForm() {

            $(".delete-item").each(function () {
                $(this).modalForm({formURL: $(this).data("form-url"), isDeleteForm: true});

            });
          }



          deleteItemModalForm();





           // modal form
          function updateItemModalForm() {
            $(".update-item").each(function () {
              $(this).modalForm({
                formURL: $(this).data("form-url"),
                asyncUpdate: false

              });
            });
          }


             // modal form
          function priseEnChargeModalForm() {
            $(".priseencharge-item").each(function () {
              $(this).modalForm({
                formURL: $(this).data("form-url"),
                 asyncUpdate: false

              });
            });
          }

          function accepterOPModalForm() {
            $(".accepter-item").each(function () {
              $(this).modalForm({
                formURL: $(this).data("form-url"),
                 asyncUpdate: false

              });
            });
          }




               // modal form
          function validateItemModalForm() {
            $(".valider-item").each(function () {
              $(this).modalForm({
                formURL: $(this).data("form-url"),
                 asyncUpdate: false

              });
            });
          }


           function deletePriseenchargeItemForm() {
            $(".delete_priseencharge-item").each(function () {
              $(this).modalForm({
                formURL: $(this).data("form-url"),
                 asyncUpdate: false

              });
            });
          }


           function changePriseenchargeItemForm() {
            $(".change_priseencharge-item").each(function () {
              $(this).modalForm({
                formURL: $(this).data("form-url"),
                 asyncUpdate: false

              });
            });
          }

          function retraiitCheckItemForm() {
            $(".retrait-cheque-item").each(function () {
              $(this).modalForm({
                formURL: $(this).data("form-url"),
                 asyncUpdate: false

              });
            });
          }

           function payerOrdreItemForm() {
            $(".payer-ordre-item").each(function () {
              $(this).modalForm({
                formURL: $(this).data("form-url"),
                 asyncUpdate: false

              });
            });
          }

          payerOrdreItemForm();
          validateItemModalForm();
          updateItemModalForm();
          priseEnChargeModalForm();
          accepterOPModalForm();
          changePriseenchargeItemForm();
          deletePriseenchargeItemForm();
          retraiitCheckItemForm();


            function reinstantiateModalForms() {

            createItemSyncModalForm();
            deleteItemModalForm();
            updateItemModalForm();
            validateItemModalForm();
            priseEnChargeModalForm();
            accepterOPModalForm();
              changePriseenchargeItemForm();
          deletePriseenchargeItemForm();
          retraiitCheckItemForm();
          payerOrdreItemForm();
          }


           $('.datetimepicker').datetimepicker({format: 'MM/DD/YYYY HH:mm:ss'});


      });