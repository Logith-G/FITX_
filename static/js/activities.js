const form=document.getElementById('activityForm');
const msg=document.getElementById('manualActivityMessage');

form?.addEventListener('submit',async (e)=>{
  e.preventDefault();
  const body={}; new FormData(form).forEach((v,k)=>body[k]=v);
  try{
    const res=await fetch('/api/activities',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
    const data=await res.json();
    if(!res.ok) throw new Error(data.error || 'Unable to save activity.');
    msg.textContent=`Saved. +${data.points} FITX points.`; msg.style.color='#15966a';
    form.reset(); form.activity_date.value=new Date().toISOString().slice(0,10);
    window.location.reload();
  }catch(err){msg.textContent=err.message; msg.style.color='#c83c50';}
});

document.addEventListener('click',async e=>{
  const btn=e.target.closest('.delete-btn'); if(!btn) return;
  const id=btn.dataset.id;
  const res=await fetch(`/api/activities/${id}`,{method:'DELETE'});
  if(res.ok) document.getElementById(`activity-${id}`)?.remove();
});
