// Persist language selection to localStorage and cookie when language links are clicked
function persistLanguage(lang){
  if(!/^(en|ar)$/.test(lang)) return;
  localStorage.setItem('site_language', lang);
  document.cookie = 'site_language='+encodeURIComponent(lang)+'; path=/; max-age='+(60*60*24*365)+'; samesite=lax';
}

document.addEventListener('click', function(e){
  var a = e.target.closest && e.target.closest('a');
  if(!a) return;
  try{
    var href = a.getAttribute('href')||'';
    if(/[?&]language=/.test(href)){
      var m = href.match(/[?&]language=([^&]+)/);
      if(m){
        var lang = decodeURIComponent(m[1]);
        persistLanguage(lang);
      }
    }
  }catch(err){}
});

// On load, if localStorage has language, but cookie not present, set cookie
try{
  var ls = localStorage.getItem('site_language');
  if(ls && document.cookie.indexOf('site_language=')===-1){
    persistLanguage(ls);
  }
}catch(e){}
