function showMessage(id, message, ok=false){
  const el=document.getElementById(id); if(!el) return;
  el.textContent=message; el.style.color=ok ? '#15966a' : '#c83c50';
}

async function sendForm(url, form, messageId){
  const body={};
  new FormData(form).forEach((v,k)=>body[k]=v);
  try{
    const res=await fetch(url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
    const data=await res.json();
    if(!res.ok) throw new Error(data.error || 'Something went wrong.');
    showMessage(messageId,data.message,true);
    return true;
  }catch(err){showMessage(messageId,err.message,false); return false;}
}

document.addEventListener('DOMContentLoaded',()=>{
  const goalForm=document.getElementById('goalForm');
  if(goalForm) goalForm.addEventListener('submit',async e=>{e.preventDefault(); await sendForm('/api/goals',goalForm,'goalMessage');});

  const profileForm=document.getElementById('profileForm');
  if(profileForm) profileForm.addEventListener('submit',async e=>{e.preventDefault(); await sendForm('/api/profile',profileForm,'profileMessage');});
});
