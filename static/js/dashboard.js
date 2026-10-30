const stats=window.FITX_DASHBOARD;

const savedReminder = window.localStorage.getItem('fitx-next-reminder');
const reminderText = document.getElementById('nextReminderText');
if (savedReminder && reminderText) {
  reminderText.textContent = `Your next reminder is set for ${savedReminder}.`;
}

if (typeof Chart !== 'undefined' && document.getElementById('mixChart')) {
const breakdown=stats.activity_breakdown || {};
new Chart(document.getElementById('mixChart'),{
  type:'doughnut',
  data:{labels:Object.keys(breakdown).length ? Object.keys(breakdown) : ['No activity yet'],datasets:[{data:Object.values(breakdown).length ? Object.values(breakdown) : [1],backgroundColor:['#c7f36b','#63e6d0','#ff765f','#a78bfa','#ffd166'],borderWidth:0}]},
  options:{responsive:true,plugins:{legend:{position:'bottom',labels:{color:'#91a1b5',padding:14}}}}
});
}

async function loadRecommendation(){
  const box=document.getElementById('recommendation');
  try{
    const res=await fetch('/api/recommendation');
    const data=await res.json();
    const breakdown=data.breakdown;
    const steps=breakdown.steps.map((step,index)=>`<li><div><strong>${index+1}. ${step.name}</strong><span>${step.minutes} min${step.repetitions?` · ${step.repetitions}`:''}</span></div><ul>${step.instructions.map(instruction=>`<li>${instruction}</li>`).join('')}</ul></li>`).join('');
    const factors=(data.explanation?.factors||[]).map(factor=>`<li>${factor}</li>`).join('');
    box.innerHTML=`<div class="recommendation-summary"><strong>${breakdown.session_name} · ${breakdown.duration} minutes</strong><span>${data.reason}</span><button class="text-link recommendation-details" type="button" aria-expanded="false">Why this session? · View details</button></div><div class="recommendation-details-panel" hidden><p><b>Why this session?</b> ${data.explanation?.reason||data.reason}</p><ul class="explanation-factors">${factors}</ul><p><b>What is it?</b> ${breakdown.what_is_it}</p><p><b>How to use this plan:</b> ${breakdown.how_to_use}</p><ol>${steps}</ol><p class="breakdown-total">Total session time: <strong>${breakdown.duration} minutes</strong></p><div class="rec-note">${data.note}</div></div>`;
    box.querySelector('.recommendation-details')?.addEventListener('click',event=>{const expanded=event.currentTarget.getAttribute('aria-expanded')==='true';event.currentTarget.setAttribute('aria-expanded',String(!expanded));box.querySelector('.recommendation-details-panel').hidden=expanded;});
  }catch(err){box.textContent='Recommendation is temporarily unavailable.';}
}
loadRecommendation();

const adaptiveStart=document.getElementById('startAdaptiveSession');
const adaptiveWhy=document.getElementById('adaptiveWhy');
const adaptiveExplanation=document.getElementById('adaptiveExplanation');
const adaptiveMessage=document.getElementById('adaptiveMessage');
const adaptiveBreakdown=document.getElementById('adaptiveBreakdown');
const adaptiveSteps=document.querySelectorAll('#adaptiveSteps .session-step');
const sessionRunner=document.getElementById('sessionRunner');
const currentStepName=document.getElementById('currentStepName');
const currentStepPosition=document.getElementById('currentStepPosition');
const currentStepInstructions=document.getElementById('currentStepInstructions');
const nextStep=document.getElementById('nextStep');
const startStepTimer=document.getElementById('startStepTimer');
const stepTimer=document.getElementById('stepTimer');
const partialSession=document.getElementById('partialSession');
const skipSession=document.getElementById('skipSession');
let currentStepIndex=0;
let stepTimerId;
let stepSeconds=0;
function showAdaptiveStep(){
  const step=adaptiveSteps[currentStepIndex];
  if(!step) return;
  adaptiveSteps.forEach(item=>item.classList.remove('current-step'));
  step.classList.add('current-step');
  currentStepName.textContent=step.querySelector('strong').textContent;
  currentStepPosition.textContent=`Step ${currentStepIndex+1} of ${adaptiveSteps.length}`;
  currentStepInstructions.textContent=Array.from(step.querySelectorAll('ul li')).map(item=>item.textContent).join(' ');
  stepSeconds=parseInt(step.querySelector('span').textContent,10)*60;
  stepTimer.textContent=`${Math.floor(stepSeconds/60)}:00`;
  startStepTimer.disabled=false;
  startStepTimer.textContent='Start timer';
  nextStep.textContent=currentStepIndex===adaptiveSteps.length-1?'Finish plan':'Next activity';
}
adaptiveWhy?.addEventListener('click',()=>{const expanded=adaptiveWhy.getAttribute('aria-expanded')==='true';adaptiveWhy.setAttribute('aria-expanded',String(!expanded));adaptiveExplanation.hidden=expanded;});
async function submitAdaptiveResult(status,completedMinutes=0){
  const response=await fetch('/api/adaptive-session/complete',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({duration:adaptiveStart.dataset.duration,activity:adaptiveStart.dataset.activity,title:adaptiveStart.dataset.title,status,completed_minutes:completedMinutes})});
  const data=await response.json();
  if(!response.ok) throw new Error(data.error||'Unable to save session result.');
  return data;
}
adaptiveStart?.addEventListener('click',async()=>{if(adaptiveStart.dataset.started!=='true'){adaptiveStart.dataset.started='true';adaptiveStart.textContent='Complete session';adaptiveBreakdown.hidden=false;sessionRunner.hidden=false;showAdaptiveStep();return;}adaptiveStart.disabled=true;try{const data=await submitAdaptiveResult('completed',Number(adaptiveStart.dataset.duration));adaptiveMessage.textContent=`Session complete. +${data.points} FITX points.`;adaptiveMessage.style.color='#15966a';setTimeout(()=>window.location.reload(),700);}catch(error){adaptiveMessage.textContent=error.message;adaptiveMessage.style.color='#c83c50';adaptiveStart.disabled=false;}});
nextStep?.addEventListener('click',()=>{if(currentStepIndex<adaptiveSteps.length-1){currentStepIndex+=1;showAdaptiveStep();}else{nextStep.disabled=true;nextStep.textContent='Plan complete';}});
startStepTimer?.addEventListener('click',()=>{clearInterval(stepTimerId);startStepTimer.disabled=true;startStepTimer.textContent='Timer running';stepTimerId=setInterval(()=>{stepSeconds-=1;stepTimer.textContent=`${Math.floor(Math.max(0,stepSeconds)/60)}:${String(Math.max(0,stepSeconds)%60).padStart(2,'0')}`;if(stepSeconds<=0){clearInterval(stepTimerId);startStepTimer.disabled=false;startStepTimer.textContent='Restart timer';}},1000);});
partialSession?.addEventListener('click',async()=>{try{await submitAdaptiveResult('partial',Math.max(1,Math.round(Number(adaptiveStart.dataset.duration)*Math.max(1,currentStepIndex)/adaptiveSteps.length)));adaptiveMessage.textContent='Partial session saved. FITX will adjust the next session gently.';adaptiveMessage.style.color='#15966a';}catch(error){adaptiveMessage.textContent=error.message;adaptiveMessage.style.color='#c83c50';}});
skipSession?.addEventListener('click',async()=>{try{await submitAdaptiveResult('skipped');adaptiveMessage.textContent='No problem. FITX will offer a manageable restart session next time.';adaptiveMessage.style.color='#15966a';}catch(error){adaptiveMessage.textContent=error.message;adaptiveMessage.style.color='#c83c50';}});
