{%comment%}Modal dialog for attach thread{%endcomment%}
<style>
#attachThreadListWrap.loading {
    display: block;
    background: url('/static/commitfest/spinner.gif') no-repeat center;
    width: 124px;
    height: 124px;
    margin: 0 auto;
}
#attachThreadListWrap.loading * {
    display: none;  
}
</style>

<div class="modal hide fade" id="attachModal" role="dialog" style="width:80%; left: 10%; margin-left:auto; margin-right: auto;">
 <div class="modal-header">
  <button type="button" class="close" data-dismiss="modal" aria-hidden="true">&times;</button>
  <h3>Attach thread</h3>
 </div>
 <div class="modal-body">
   <form class="form-search" style="margin-bottom: 5px;">
     <div class="input-append">
       <input id="attachThreadSearchField" type="text" class="span2 search-query">
       <button id="attachThreadSearchButton" onclick="return findLatestThreads()" class="btn disabled">Search</button>
     </div>
   </form>
   <div>Pick one of the recent emails from pgsql-hackers, or search above for subject or name:</div>
   <div id="attachThreadListWrap">
     <select id="attachThreadList" size="6" style="width:100%;" onchange="attachThreadChanged()">
     </select>
   </div>
   <div>Or enter an <i>exact</i> message id:</div>
   <input type="text" id="attachThreadMessageId" placeholder="Message id" class="input-block-level" onkeypress="attachThreadChanged()" onchange="attachThreadChanged()">
 </div>
 <div class="modal-footer">
   <a href="#" class="btn" data-dismiss="modal">Close</a>
   <a href="#" id="doAttachThreadButton" class="btn btn-primary disabled">Attach thread</a>
 </div>
</div>
