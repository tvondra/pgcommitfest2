<div style="margin-bottom:5px;">
<a class="btn" href="edit/">Edit</a>

<div class="btn-group">
 <a class="btn dropdown-toggle" data-toggle="dropdown" href="#">Comment <span class="caret"></span></a>
 <ul class="dropdown-menu">
  <li><a href="comment/">Comment</a>
  <li><a href="review/">Review</a>
 </ul>
</div>

<div class="btn-group">
 <a class="btn dropdown-toggle" data-toggle="dropdown" href="#">Status <span class="caret"></span></a>
 <ul class="dropdown-menu">
  <li><a href="status/review/">Needs review</a></li>
  <li><a href="status/author/">Waiting on Author</a></li>
  <li><a href="status/committer/"">Ready for Committer</a></li>
 </ul>
</div>

<div class="btn-group">
 <a class="btn dropdown-toggle" data-toggle="dropdown" href="#">Close <span class="caret"></span></a>
 <ul class="dropdown-menu">
  <li><a href="close/reject/" onclick="return verify_reject()">Rejected</a></li>
  <li><a href="close/feedback/" onclick="return verify_returned()">Returned with feedback</a></li>
  <li><a href="close/committed/" onclick="return verify_committed({{is_committer|yesno:"true,false"}}))">Committed</a></li>
 </ul>
</div>

</div>