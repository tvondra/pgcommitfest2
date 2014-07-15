function verify_reject() {
   return confirm('Are you sure you want to close this patch as Rejected?\n\nThis should only be done when a patch will never be applied - if more work is needed, it should instead be set to "Returned with Feedback".\n\nSo - are you sure?');
}
function verify_returned() {
   return confirm('Are you sure you want to close this patch as Returned with Feedback?\n\nThis means the patch will be marked as closed in this commitfest, but will automatically be moved to the next one. If no further work is expected on this patch, it should be closed with "Rejected" istead.\n\nSo - are you sure?');
}

function findLatestThreads() {
   $('#attachThreadListWrap').addClass('loading');
   $('#attachThreadSearchButton').addClass('disabled');
   $.get('/ajax/getThreads/', {
      's': $('#attachThreadSearchField').val(),
   }).success(function(data) {
         sel = $('#attachThreadList');
         sel.find('option').remove();
         $.each(data, function(m,i) {
            sel.append('<option value="' + i.msgid + '">' + i.from + ': ' + i.subj + ' (' + i.date + ')</option>');
         });
   }).always(function() {
      $('#attachThreadListWrap').removeClass('loading');
      $('#attachThreadSearchButton').removeClass('disabled');
      attachThreadChanged();
   });
   return false;
}

function browseThreads(attachfunc) {
   $('#attachThreadList').find('option').remove();
   $('#attachThreadMessageId').val('');
   $('#attachModal').modal();
   findLatestThreads();

   $('#doAttachThreadButton').unbind('click');
   $('#doAttachThreadButton').click(function() {
      msgid = $('#attachThreadMessageId').val();
      if (!msgid || msgid == '') {
         msgid = $('#attachThreadList').val();
         if (!msgid) return;
      }

      $('#attachThreadListWrap').addClass('loading');
      $('#attachThreadSearchButton').addClass('disabled');
      $('#attachThreadButton').addClass('disabled');
      if (attachfunc(msgid)) {
         $('#attachModal').modal('hide');
      }
      $('#attachThreadListWrap').removeClass('loading');
      $('#attachThreadSearchButton').removeClass('disabled');
      attachThreadChanged();
   });

}

function attachThread(cfid, patchid) {
   browseThreads(function(msgid) {
      doAttachThread(cfid, patchid, msgid);
   });
}

function detachThread(cfid, patchid, msgid) {
   if (confirm('Are you sure you want to detach the thread with messageid "' + msgid + '" from this patch?')) {
      $.post('/ajax/detachThread/', {
         'cf': cfid,
         'p': patchid,
         'msg': msgid,
      }).success(function(data) {
         location.reload();
      }).fail(function(data) {
         alert('Failed to detach thread!');
      });
   }
}

function attachThreadChanged() {
   if ($('#attachThreadList').val() || $('#attachThreadMessageId').val()) {
      $('#doAttachThreadButton').removeClass('disabled');
   }
   else {
      $('#doAttachThreadButton').addClass('disabled');
   }
}

function doAttachThread(cfid, patchid, msgid) {
   $.post('/ajax/attachThread/', {
      'cf': cfid,
      'p': patchid,
      'msg': msgid,
   }).success(function(data) {
      location.reload();
      return true;
   }).fail(function(data) {
      if (data.status == 404) {
         alert('Message with messageid ' + msgid + ' not found');
      }
      else if (data.status == 503) {
         alert('Failed to attach thread: ' + data.responseText);
      }
      else {
         alert('Failed to attach thread: ' + data.statusText);
      }
      return false;
   });
}

function flagCommitted(committer) {
   $('#commitModal').modal();
   $('#committerSelect').val(committer);
   $('#doCommitButton').unbind('click');
   $('#doCommitButton').click(function() {
       var c = $('#committerSelect').val();
       if (!c) {
	   alert('You need to select a committer before you can mark a patch as committed!');
	   return;
       }
       document.location.href='close/committed/?c=' + c;
   });
   return false;
}


function sortpatches(sortby) {
   $('#id_sortkey').val(sortby);
   $('#filterform').submit();

   return false;
}

function toggleButtonCollapse(buttonId, collapseId) {
   $('#' + buttonId).button('toggle');
   $('#' + collapseId).toggleClass('in')
}
