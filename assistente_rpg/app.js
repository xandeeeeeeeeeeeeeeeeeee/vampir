'use strict';
const $=id=>document.getElementById(id);
const types={personagem:'Personagem',npc:'NPC',local:'Local',faccao:'Facção',relacao:'Relação',regra:'Regra da casa',segredo:'Segredo',sessao:'Sessão',acontecimento:'Acontecimento',trama:'Trama',cheat_sheet:'Cheat sheet',nota:'Nota privada'};
const states={rascunho:'Rascunho',alternativa:'Alternativa',planejado:'Planejado',confirmado:'Confirmado'};
const attrs=['Força','Destreza','Vigor','Carisma','Manipulação','Autocontrole','Inteligência','Raciocínio','Determinação'];
const skills=['Armas Brancas','Armas de Fogo','Atletismo','Briga','Condução','Furtividade','Ladinagem','Ofícios','Sobrevivência','Empatia','Etiqueta','Intimidação','Liderança','Manha','Performance','Persuasão','Subterfúgio','Trato com Animais','Ciência','Erudição','Finanças','Investigação','Medicina','Ocultismo','Percepção','Política','Tecnologia'];
const resources=['fome','humanidade','potencia_sangue','gravidade_perdicao','vitalidade','forca_vontade','dano_superficial','dano_agravado'];
let user=null, records=[], users=[], proposals=[], selected=new Set(), editing=null, proposalEdit=null, activeProposal=null, task=null, tab='conversa';
function node(tag,text,cls){const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(cls)n.className=cls;return n}
function button(text,fn,cls){const b=node('button',text,cls);b.type='button';b.onclick=()=>Promise.resolve(fn()).catch(notify);return b}
function notify(error){$('notice').hidden=false;$('notice').textContent=error.message||String(error);}
async function api(path,data){const response=await fetch(path,{method:data===undefined?'GET':'POST',headers:{'Content-Type':'application/json',...(user?{'X-CSRF':user.csrf}:{})},...(data===undefined?{}:{body:JSON.stringify(data)})});let value=await response.json();if(!response.ok){if(response.status===401&&user){user=null;$('app').hidden=true;$('login').hidden=false}throw Error(value.erro||'Solicitação recusada')}return value}
function master(){return user?.role==='mestre'}
function playerContext(r){return !r.archived&&((['personagem','nota','cheat_sheet'].includes(r.kind)&&r.owners.includes(user.id))||(['cheat_sheet','regra'].includes(r.kind)&&(r.all_players||r.audience.includes(user.id))))}
function setRole(){document.body.dataset.role=user.role;$('new-record').hidden=!master();
 const tool=$('tool').value,model=$('model').value;
 const options=master()?[['conversa','Conversa'],['consultor','Consultor de regras'],['criador','Criador'],['planejador','Planejador de sessões'],['continuidade','Analista de continuidade']]:[['consultor','Dúvidas de regras'],['criador','Minha ficha e materiais'],['conversa','Interpretação do meu personagem']];
 choose('tool',options,[options.some(x=>x[0]===tool)?tool:options[0][0]]);
 choose('model',master()?[['conversa','Gemma 12B · conversa'],['extenso','Gemma 26B · trabalho extenso']]:[['conversa','Gemma 12B']], [master()?model:'conversa']);
 $('model-choice').hidden=!master();$('chat-title').textContent=master()?'Planejamos juntos.':'Ajuda para seu personagem.';
 $('chat-description').textContent=master()?'Converse, explore alternativas e decida o que entra na sua crônica.':'Consulte regras, prepare sua ficha e explore a interpretação. Campanha, NPCs e decisões de cena ficam com o mestre.';
 $('question').placeholder=master()?'Vamos criar uma facção com interesses conflitantes…':'Como funciona esta regra? Ajude com minha ficha ou com a intenção do meu personagem…';
 $('context-description').textContent=master()?'Selecione até 12 registros para incluir no pedido.':'Selecione até quatro fichas, notas ou referências pessoais. A IA não recebe o planejamento da campanha.';
}
function empty(where,text){where.append(node('div',text,'empty'))}
function choose(id,values,selectedValues=[]){const s=$(id);s.replaceChildren();for(const [value,label] of values){const o=node('option',label);o.value=value;o.selected=selectedValues.includes(value);s.append(o)}}
function picks(id){return [...$(id).selectedOptions].map(x=>x.value)}
function recordName(id){return records.find(x=>x.id===id)?.name||'Registro indisponível'}
function switchTab(next){tab=next;if(next==='mapa')loadMap().catch(notify);if(next==='calendario')loadCalendar().catch(notify);document.querySelectorAll('.tab').forEach(x=>x.hidden=x.id!==next);document.querySelectorAll('#nav button').forEach(x=>x.classList.toggle('selected',x.dataset.tab===next));}
document.querySelectorAll('#nav button').forEach(b=>b.onclick=()=>switchTab(b.dataset.tab));
document.querySelectorAll('[data-close]').forEach(b=>b.onclick=()=>$(b.dataset.close).close());

async function load(){records=await api('/api/registros?arquivados='+($('show-archived').checked?'1':'0'));if(master())users=await api('/api/contas');proposals=await api('/api/propostas');
const campaign=await api('/api/campanha');$('campaign-title').textContent=campaign.titulo;render();await messages();if(tab==='mapa')await loadMap();if(tab==='calendario')await loadCalendar();}
function card(r){const b=button('',()=>edit(r),'card');const tags=node('div',undefined,'tags');tags.append(node('span',types[r.kind],'tag'),node('span',states[r.state],'tag'));if(r.archived)tags.append(node('span','Arquivado','tag archived'));b.append(tags,node('h3',r.name),node('p',r.summary||'Sem resumo.'));if(['personagem','npc'].includes(r.kind)){const s=r.sheet;b.append(node('p',[s.cla,s.papel].filter(Boolean).join(' · ')));const chips=node('div',undefined,'tags');for(const [k,v] of Object.entries(s.recursos||{}))chips.append(node('span',k.replaceAll('_',' ')+': '+v,'tag'));b.append(chips)}return b}
function render(){const query=$('filter').value.toLocaleLowerCase(),kind=$('kind-filter').value;const visible=records.filter(r=>(!kind||r.kind===kind)&&[r.name,r.summary,r.content].join(' ').toLocaleLowerCase().includes(query));
$('records').replaceChildren(...visible.map(card));if(!visible.length)empty($('records'),'Nenhum registro. Comece criando um local, uma facção ou uma ideia.');
$('characters').replaceChildren(...records.filter(r=>['personagem','npc'].includes(r.kind)).map(card));if(!$('characters').children.length)empty($('characters'),'As pessoas da sua crônica aparecerão aqui.');
$('notes').replaceChildren(...records.filter(r=>r.kind==='nota'&&r.owners.includes(user.id)).map(card));
$('materials').replaceChildren(...records.filter(r=>r.kind==='cheat_sheet').map(card));
$('board').replaceChildren();for(const [state,label] of Object.entries(states)){const col=node('div',undefined,'board-column');col.append(node('h3',label));for(const r of records.filter(r=>r.kind==='sessao'&&r.state===state))col.append(card(r));$('board').append(col)}
$('timeline').replaceChildren();for(const r of records.filter(r=>r.kind==='acontecimento').sort((a,b)=>a.date.localeCompare(b.date))){const item=node('div',undefined,'timeline-item');item.append(node('small',(r.date||'Sem data')+' · '+states[r.state]),button(r.name,()=>edit(r)));$('timeline').append(item)}if(!$('timeline').children.length)empty($('timeline'),'Adicione acontecimentos planejados ou confirmados para construir a linha do tempo.');
graph();renderContext();renderProposals();setRole();}
function graph(){const target=$('graph');target.replaceChildren();const connected=records.filter(r=>r.links.length||records.some(x=>x.links.includes(r.id)));if(!connected.length){empty(target,'Crie referências entre registros para visualizar as conexões.');return}
const ns='http://www.w3.org/2000/svg',svg=document.createElementNS(ns,'svg');const width=650,height=Math.max(180,Math.ceil(connected.length/3)*90);svg.setAttribute('viewBox',`0 0 ${width} ${height}`);svg.style.minWidth='500px';const positions=new Map(connected.map((r,i)=>[r.id,{x:20+(i%3)*215,y:20+Math.floor(i/3)*90}]));for(const r of connected)for(const link of r.links){const a=positions.get(r.id),b=positions.get(link);if(!b)continue;const line=document.createElementNS(ns,'line');for(const [k,v] of Object.entries({x1:a.x+90,y1:a.y+20,x2:b.x+90,y2:b.y+20}))line.setAttribute(k,v);svg.append(line)}for(const r of connected){const p=positions.get(r.id),g=document.createElementNS(ns,'g');g.setAttribute('role','button');g.setAttribute('tabindex','0');g.setAttribute('aria-label',r.name);g.onclick=()=>edit(r);g.onkeydown=e=>{if(e.key==='Enter')edit(r)};const rect=document.createElementNS(ns,'rect');for(const [k,v] of Object.entries({x:p.x,y:p.y,width:185,height:44,rx:6}))rect.setAttribute(k,v);const text=document.createElementNS(ns,'text');text.setAttribute('x',p.x+10);text.setAttribute('y',p.y+27);text.textContent=r.name.slice(0,24);const title=document.createElementNS(ns,'title');title.textContent=r.name;g.append(rect,text,title);svg.append(g)}target.append(svg);const links=node('div',undefined,'graph-links');for(const r of connected)for(const id of r.links)links.append(button(r.name+' → '+recordName(id),()=>edit(r)));target.append(links)}
function renderContext(){$('context').replaceChildren();const allowed=records.filter(r=>master()?!r.archived:playerContext(r));const ids=new Set(allowed.map(r=>r.id));selected=new Set([...selected].filter(id=>ids.has(id)));for(const r of allowed){const label=node('label',undefined,'check'),input=node('input');input.type='checkbox';input.checked=selected.has(r.id);input.onchange=()=>{const limit=master()?12:4;if(input.checked&&selected.size>=limit){input.checked=false;notify('Selecione até '+limit+' registros.');return}input.checked?selected.add(r.id):selected.delete(r.id)};label.append(input,node('span',r.name+' · '+types[r.kind]));$('context').append(label)}}
function renderProposals(){$('proposals').replaceChildren();for(const p of proposals.filter(x=>x.status==='pendente')){const row=node('div',undefined,'proposal-card');row.append(button(p.after.name,()=>review(p)),node('small',p.motivo));$('proposals').append(row)}if(!$('proposals').children.length)$('proposals').append(node('p','Nenhuma proposta pendente.','muted'))}
async function messages(){const all=await api('/api/mensagens');$('messages').replaceChildren();for(const m of all){const n=node('article',undefined,'message');n.append(node('p',m.pergunta,'question'),node('pre',m.resposta));n.append(node('small',m.modelo+' · '+m.duracao+' s'));for(const source of m.fontes)n.append(button('Fonte '+source,async()=>{switchTab('biblioteca');await showSource(source)}));$('messages').append(n)}if(!all.length)empty($('messages'),master()?'Experimente: “Vamos planejar uma primeira sessão centrada numa dívida entre duas facções.” A IA só inicia quando você enviar um pedido.':'Experimente: “Explique os dados de Fome” ou “Ajude a montar minha ficha”. A IA não decide cenas nem altera a campanha.');}
function numeric(container,names,values,max){container.replaceChildren();for(const name of names){const label=node('label',name),input=node('input');input.type='number';input.min=0;input.max=max;input.dataset.name=name;input.value=values?.[name]??'';label.append(input);container.append(label)}}
function numbers(id){const output={};for(const n of $(id).querySelectorAll('input'))if(n.value!=='')output[n.dataset.name]=Number(n.value);return output}
function discipline(name='',value=''){const row=node('div',undefined,'discipline'),text=node('input'),number=node('input');text.placeholder='Nome da disciplina';text.value=name;text.className='discipline-name';number.type='number';number.min=0;number.max=20;number.value=value;number.className='discipline-value';row.append(text,number,button('Remover',()=>row.remove()));$('disciplines').append(row)}
$('add-discipline').onclick=()=>discipline();
function fresh(kind){return {id:crypto.randomUUID(),kind,name:'',summary:'',origin:'criacao',state:'rascunho',date:'',links:[],owners:[],audience:[],all_players:false,archived:false,sheet:{},content:'',master_notes:'',sources:[],version:0}}
function summary(r){return [r.name,types[r.kind]+' · '+states[r.state],r.summary,r.content,...Object.entries(r.sheet||{}).map(([k,v])=>k.replaceAll('_',' ')+': '+(typeof v==='object'?JSON.stringify(v,null,2):v)),...(r.master_notes?['Notas do mestre: '+r.master_notes]:[])].filter(Boolean).join('\n\n')}
function edit(r,proposal=null){editing=structuredClone(r);proposalEdit=proposal;$('editor-title').textContent=r.version?'Editar '+r.name:'Novo '+types[r.kind];$('edit-error').textContent='';
for(const [id,key] of Object.entries({'e-name':'name','e-summary':'summary','e-content':'content','e-date':'date','e-secret':'master_notes'}))$(id).value=r[key]||'';
$('e-kind').value=r.kind;$('e-origin').value=r.origin;$('e-state').value=r.state;$('e-all').checked=r.all_players;$('e-sources').value=(r.sources||[]).join(', ');
choose('e-links',records.filter(x=>x.id!==r.id).map(x=>[x.id,x.name]),r.links);choose('e-owners',users.filter(x=>x.role==='jogador'&&x.active).map(x=>[x.id,x.name]),r.owners);choose('e-audience',users.filter(x=>x.role==='jogador'&&x.active).map(x=>[x.id,x.name]),r.audience);
const c=r.sheet?.cartografia||{};$('m-enabled').checked=!!r.sheet?.cartografia;for(const k of ['tipo','territorio','x','y','largura','altura'])$('m-'+k).value=c[k]??({tipo:'local',territorio:'',x:50,y:50,largura:20,altura:20}[k]);const s=r.sheet||{};renderCreation(s.criacao);for(const key of ['cla','papel','conceito','condicoes','historico','notas'])$('s-'+key).value=s[key]||'';numeric($('attributes'),attrs,s.atributos,20);numeric($('skills'),skills,s.habilidades,20);numeric($('resources'),resources,s.recursos,100);$('disciplines').replaceChildren();for(const [k,v] of Object.entries(s.disciplinas||{}))discipline(k,v);choose('s-rule',[['','Limites V5 padrão'],...records.filter(x=>x.kind==='regra'&&!x.archived).map(x=>[x.id,x.name])],[s.regra_da_casa||'']);
numeric($('rule-limits'),['atributos','habilidades','disciplinas','fome','humanidade','potencia_sangue'],s.limites,20);
$('complete-existing').hidden=r.kind!=='personagem'||r.archived||!!r.sheet.criacao||(!master()&&!r.owners.includes(user.id));const canEdit=master()||(['personagem','nota','cheat_sheet'].includes(r.kind)&&r.owners.includes(user.id)&&!r.archived)||(['personagem','nota','cheat_sheet'].includes(r.kind)&&!r.version);
$('editor-title').textContent=r.version?(canEdit?'Editar ':'')+r.name:'Novo '+types[r.kind];
for(const input of $('edit-form').querySelectorAll('input,textarea,select'))input.disabled=!canEdit;
for(const id of ['e-kind','e-origin','e-state','e-date','s-rule'])$(id).disabled=!master();$('save-record').hidden=!canEdit;$('archive').hidden=!master()||!r.version||!!proposal;$('archive').textContent=r.archived?'Restaurar da lista de arquivados':'Arquivar';$('history').hidden=!r.version||!!proposal;$('export-md').hidden=!r.version||!!proposal;$('export-html').hidden=!r.version||!!proposal;$('save-record').textContent=proposal?'Aceitar versão editada':'Salvar alterações';
$('edit-fields').hidden=r.kind==='cheat_sheet'&&!canEdit;drawGuide(r);$('sheet-preview').replaceChildren();if(['npc','personagem'].includes(r.kind)){const p=node('div',undefined,'sheet-summary');p.append(node('h3','Resumo da ficha'));for(const [name,value] of Object.entries(s.atributos||{}))p.append(node('p',name+' '+('●'.repeat(Math.min(value,20))),'dots'));$('sheet-preview').append(p)}toggleKind();setRole();$('editor').showModal();}
function toggleKind(){$('map-editor').hidden=!master()||$('e-kind').value!=='local';$('sheet-editor').hidden=!['personagem','npc'].includes($('e-kind').value);$('rule-editor').hidden=!master()||$('e-kind').value!=='regra';}
$('e-kind').onchange=toggleKind;
function collect(){const r=structuredClone(editing);for(const [id,key] of Object.entries({'e-name':'name','e-summary':'summary','e-content':'content','e-date':'date','e-secret':'master_notes'}))if(master()||!['date','master_notes'].includes(key))r[key]=$(id).value;
if(master()){r.kind=$('e-kind').value;r.origin=$('e-origin').value;r.state=$('e-state').value;r.links=picks('e-links');r.owners=picks('e-owners');r.audience=picks('e-audience');r.all_players=$('e-all').checked;r.sources=$('e-sources').value.split(',').map(x=>x.trim()).filter(Boolean)}
if(['personagem','npc'].includes(r.kind)){if(r.sheet.criacao)r.sheet.criacao=readCreation(r.sheet.criacao);for(const key of ['cla','papel','conceito','condicoes','historico','notas'])r.sheet[key]=$('s-'+key).value;r.sheet.atributos=numbers('attributes');r.sheet.habilidades=numbers('skills');r.sheet.recursos=numbers('resources');r.sheet.disciplinas={};for(const row of $('disciplines').children){const name=row.querySelector('.discipline-name').value.trim(),value=row.querySelector('.discipline-value').value;if(name&&value!=='')r.sheet.disciplinas[name]=Number(value)}if(master()){if($('s-rule').value)r.sheet.regra_da_casa=$('s-rule').value;else delete r.sheet.regra_da_casa}}
if(master()&&r.kind==='regra')r.sheet.limites=numbers('rule-limits');if(master()&&r.kind==='local'){if($('m-enabled').checked){r.sheet.cartografia={tipo:$('m-tipo').value,territorio:$('m-territorio').value};for(const k of ['x','y','largura','altura'])r.sheet.cartografia[k]=Number($('m-'+k).value)}else delete r.sheet.cartografia}return r;}
$('edit-form').onsubmit=async e=>{e.preventDefault();try{const r=collect(),result=proposalEdit?await api('/api/decidir',{id:proposalEdit.id,acao:'aceitar',registro:r}):await api('/api/registro',{registro:r,versao:editing.version});$('editor').close();await load();const affected=result.afetados||result.resultado?.afetados||[];notify(affected.length?'Salvo. Verifique registros afetados: '+affected.map(recordName).join(', '):'Salvo com histórico de versão.')}catch(error){$('edit-error').textContent=error.message}};
$('archive').onclick=async()=>{try{const r=structuredClone(editing);r.archived=!r.archived;await api('/api/registro',{registro:r,versao:r.version});$('editor').close();await load();notify(r.archived?'Registro arquivado; histórico preservado.':'Registro restaurado.')}catch(e){$('edit-error').textContent=e.message}};
$('history').onclick=async()=>{try{const versions=await api('/api/revisoes?id='+encodeURIComponent(editing.id));$('version-list').replaceChildren();for(const v of versions){const row=node('div',undefined,'version');row.append(node('h3','Versão '+v.after.version+' · '+new Date(v.created*1000).toLocaleString()),node('pre',summary(v.after)));if(master())row.append(button('Restaurar esta versão',async()=>{await api('/api/restaurar',{id:editing.id,revisao:v.id,versao:editing.version});$('versions').close();$('editor').close();await load();notify('Restaurado como uma nova versão.')}));$('version-list').append(row)}$('versions').showModal()}catch(e){notify(e)}};
async function exportRecord(format){const response=await fetch('/api/exportar?id='+encodeURIComponent(editing.id)+'&formato='+format);if(!response.ok)throw Error('Não foi possível exportar.');const blob=await response.blob(),url=URL.createObjectURL(blob);const link=document.createElement('a');link.href=url;link.download=editing.name.replace(/[^\p{L}\p{N} _-]/gu,'')+'.'+format;link.click();setTimeout(()=>URL.revokeObjectURL(url),10000);notify(format==='html'?'Abra o HTML baixado e use Imprimir para salvar PDF.':'Markdown baixado. As notas do mestre não integram a exportação compartilhável.')}
$('export-md').onclick=()=>exportRecord('md').catch(notify);$('export-html').onclick=()=>exportRecord('html').catch(notify);
function review(p){activeProposal=p;const canAccept=master()||(['personagem','nota','cheat_sheet'].includes(p.after.kind)&&(!p.before||p.before.owners.includes(user.id)));$('proposal-accept').hidden=!canAccept;$('proposal-edit').hidden=!canAccept;$('proposal-reason').textContent=p.motivo;$('proposal-before').textContent=p.before?summary(p.before):'Novo registro';$('proposal-after').textContent=summary(p.after);$('proposal-affected').textContent='Registros afetados: '+(p.afetados.map(recordName).join(', ')||'nenhum vínculo registrado');$('proposal').showModal()}
$('proposal-accept').onclick=async()=>{try{await api('/api/decidir',{id:activeProposal.id,acao:'aceitar'});$('proposal').close();await load();notify('Proposta aceita.')}catch(e){notify(e)}};
$('proposal-edit').onclick=()=>{$('proposal').close();edit(activeProposal.after,activeProposal)};
$('proposal-discard').onclick=async()=>{try{await api('/api/decidir',{id:activeProposal.id,acao:'descartar'});$('proposal').close();await load()}catch(e){notify(e)}};
function drawContext(context,target){
 const article=node('article',undefined,'message book-context');
 article.append(node('h3',context.titulo),node('p',context.caminho.join(' › ')),node('small','Seção completa · '+context.trechos.length+' blocos · páginas PDF '+context.paginas_pdf.join(', ')));
 const actions=node('div',undefined,'book-actions');if(bookStack.length)actions.append(button('← Voltar à leitura anterior',backBook));
 if(context.escopo!=='capitulo')actions.append(button('Ler capítulo completo',()=>showSource(context.principal,'capitulo')));
 else actions.append(button('Voltar à seção',()=>showSource(context.principal)));
 article.append(actions);
 for(const t of context.trechos){const block=node('section',undefined,t.id===context.principal?'source-hit':'');block.append(node('h4',t.titulo),node('small','ID: '+t.id+' · página PDF '+t.pagina_pdf+(t.pagina_impressa?' · página impressa '+t.pagina_impressa:'')),bookText(t.texto));const follow=node('div',undefined,'book-actions');follow.append(button('Abrir seção deste trecho',()=>showSource(t.id)),button('Ler página completa',()=>showPage(t.pagina_pdf,'pdf')));block.append(follow);article.append(block)}
 if(context.relacionados.length){article.append(node('h4','Referências citadas — continuar a leitura'));for(const r of context.relacionados)article.append(button(r.titulo+' · PDF '+r.pagina_pdf,()=>showSource(r.id)))}
 target.append(article);
}
async function showSource(id,scope='secao'){try{const epoch=++bookEpoch;const context=await api('/api/contexto?id='+encodeURIComponent(id)+'&escopo='+scope);if(epoch!==bookEpoch)return;rememberBook();$('book-results').replaceChildren();drawContext(context,$('book-results'));switchTab('biblioteca')}catch(e){notify(e)}}
$('search-form').onsubmit=async e=>{e.preventDefault();try{const hits=await api('/api/buscar?q='+encodeURIComponent($('book-query').value));$('book-results').replaceChildren();for(const [i,h] of hits.entries()){const context=h.contexto_completo;const details=node('details',undefined,'book-result');details.open=i===0;details.append(node('summary',context.caminho.join(' › ')+' · '+context.paginas_pdf.length+' página(s)'));drawContext(context,details);$('book-results').append(details)}if(!hits.length)empty($('book-results'),'Nenhuma seção encontrada. Tente outro termo.')}catch(e){notify(e)}};
async function refreshAI(){const state=await api('/api/ia');task=state.ativa||task;$('ask').disabled=state.ocupada;$('cancel').hidden=!state.ativa;$('ai-label').textContent=state.ocupada&&!state.ativa?'Outro participante está usando a IA. Você poderá enviar seu pedido quando terminar.':'IA disponível sob demanda. O modelo é liberado ao terminar.';}
function draftText(raw){const match=raw.match(/"resposta"\s*:\s*"((?:\\.|[^"\\])*)/s);if(!match)return 'Preparando a resposta…';try{return JSON.parse('"'+match[1]+'"')}catch{return match[1].replace(/\\n/g,'\n').replace(/\\"/g,'"')}}
$('cancel').onclick=async()=>{try{await api('/api/ia/controle',{acao:'cancelar'});notify('Cancelamento solicitado.')}catch(e){notify(e)}};
$('chat-form').onsubmit=async e=>{e.preventDefault();try{const job=await api('/api/ia/tarefa',{pergunta:$('question').value,papel:$('tool').value,perfil:$('model').value,selecionados:[...selected],consultar_livro:$('use-book').checked});task=job.id;sessionStorage.setItem('assistente-tarefa',task);$('ask').disabled=true;$('cancel').hidden=false;poll()}catch(e){notify(e)}};
async function poll(){if(!task)return;try{const job=await api('/api/tarefa/'+task);$('processing').hidden=false;$('task-label').textContent=job.etapa+' · '+job.segundos+' s · '+job.porcentagem+'% estimado';$('progress').value=job.porcentagem;$('partial').textContent=draftText(job.parcial||'');if(job.status==='trabalhando'||job.liberando_modelo){setTimeout(poll,1200);return}task=null;sessionStorage.removeItem('assistente-tarefa');if(job.erro)notify(job.erro);if(job.aviso)notify(job.aviso);await load();await refreshAI()}catch(e){task=null;sessionStorage.removeItem('assistente-tarefa');notify(e);await refreshAI().catch(()=>{})}}
$('filter').oninput=render;$('kind-filter').onchange=render;$('show-archived').onchange=()=>load().catch(notify);
$('new-record').onclick=()=>edit(fresh('local'));$('new-character').onclick=()=>edit(fresh('personagem'));$('new-session').onclick=()=>edit(fresh('sessao'));$('new-cheat').onclick=()=>edit(fresh('cheat_sheet'));$('new-note').onclick=()=>{const r=fresh('nota');r.owners=[user.id];edit(r)};
$('rename').onclick=async()=>{const title=prompt('Título da campanha',$('campaign-title').textContent);if(title)try{await api('/api/campanha',{titulo:title,sistema:'Vampiro: A Máscara V5'});await load()}catch(e){notify(e)}};
async function accounts(){users=await api('/api/contas');$('account-list').replaceChildren();for(const account of users){const row=node('div',undefined,'version');row.append(node('p',account.name+' · '+account.role+' · '+(account.active?'ativo':'revogado')));if(account.role==='jogador'&&account.active)row.append(button('Revogar acesso',async()=>{await api('/api/revogar',{id:account.id});await accounts();await load()}));$('account-list').append(row)}}
$('accounts').onclick=async()=>{try{await accounts();$('account-dialog').showModal()}catch(e){notify(e)}};
$('account-form').onsubmit=async e=>{e.preventDefault();try{await api('/api/conta',{name:$('account-name').value,password:$('account-password').value});$('account-form').reset();await accounts();notify('Conta criada. Entregue as credenciais diretamente ao jogador.')}catch(e){notify(e)}};
$('logout').onclick=async()=>{try{await api('/api/logout',{});location.reload()}catch(e){notify(e)}};
async function enter(){user=await api('/api/me');$('login').hidden=true;$('app').hidden=false;$('identity').textContent=user.name+' · '+user.role;switchTab('conversa');await load();await refreshAI();if(task)poll();}
$('login-form').onsubmit=async e=>{e.preventDefault();try{const status=await api('/api/status');if(!status.configurado)await api('/api/setup',{name:$('username').value,password:$('password').value});await api('/api/login',{name:$('username').value,password:$('password').value});$('password').value='';await enter()}catch(e){$('login-error').textContent=e.message}};
choose('e-kind',Object.entries(types));choose('kind-filter',[['','Todos'],...Object.entries(types)]);
(async()=>{try{await enter()}catch(e){const state=await api('/api/status');$('login-title').textContent=state.configurado?'Entrar':'Crie seu acesso de mestre';$('login-submit').textContent=state.configurado?'Entrar':'Criar acesso';$('password').autocomplete=state.configurado?'current-password':'new-password';$('login').hidden=false;$('app').hidden=true}})().catch(e=>{$('login-error').textContent=e.message});

setInterval(()=>{if(user&&!task)refreshAI().catch(()=>{});},4000);

function drawGuide(record){
 const target=$('guide-view');target.replaceChildren();target.hidden=record.kind!=='cheat_sheet';if(target.hidden)return;
 target.append(node('p',record.summary,'muted'));let list=null;
 for(const line of record.content.split('\n')){
  if(!line.trim()){list=null;continue}
  const heading=line.match(/^(#{1,3})\s+(.*)$/),item=line.match(/^(-|\d+\.)\s+(.*)$/);
  if(heading){list=null;target.append(node(heading[1].length===1?'h3':'h4',heading[2]));continue}
  if(item){const kind=item[1]==='-'?'ul':'ol';if(!list||list.tagName.toLowerCase()!==kind){list=node(kind);target.append(list)}list.append(node('li',item[2]));continue}
  list=null;target.append(node('p',line));
 }
 const ids=[...new Set(record.content.match(/p\d{4}-t\d{3}/g)||[])];
 for(const id of ids)target.append(button('Consultar fonte '+id,async()=>{$('editor').close();switchTab('biblioteca');await showSource(id)}));
}

let atlas=null;
async function loadMap(){
 atlas=await api('/api/mapa?visao='+(master()?$('map-view').value:'atual'));
 $('map-label').textContent=atlas.visao==='mestre'?'Mestre: inclui locais ocultos e anotações privadas.':'Jogadores: somente locais e informações autorizados. A prévia do mestre mostra apenas o material liberado a todos.';
 $('map-details').replaceChildren();
 const ns='http://www.w3.org/2000/svg',svg=document.createElementNS(ns,'svg');svg.setAttribute('viewBox','0 0 1000 720');svg.setAttribute('aria-label','Mapa esquemático da cidade');svg.setAttribute('role','img');
 const shape=(tag,props)=>{const n=document.createElementNS(ns,tag);for(const [k,v] of Object.entries(props))n.setAttribute(k,String(v));return n};
 for(const r of [...atlas.registros].sort((a,b)=>(a.sheet.cartografia.tipo==='distrito'?0:1)-(b.sheet.cartografia.tipo==='distrito'?0:1))){
  const c=r.sheet.cartografia,x=c.x*9+40,y=c.y*6+40,g=shape('g',{tabindex:0,role:'button','aria-label':r.name});
  const district=c.tipo==='distrito';
  g.append(shape(district?'rect':'circle',district?{x,y,width:c.largura*9,height:c.altura*6,rx:10}:{cx:x,cy:y,r:8}));
  const t=shape('text',{x:x+(district?12:14),y:y+(district?24:4)});t.textContent=r.name;g.append(t);
  const title=shape('title',{});title.textContent=r.name+' — '+r.summary;g.append(title);
  const select=()=>{const panel=node('article',undefined,'card');panel.append(node('h3',r.name),node('p',r.summary),node('p',r.content),node('p','Território: '+(c.territorio||'não anotado')));if(r.master_notes)panel.append(node('h4','Notas do mestre'),node('p',r.master_notes));if(master()&&atlas.visao==='mestre')panel.append(button('Editar local e anotações',()=>edit(r)));$('map-details').replaceChildren(panel)};
  g.onclick=select;g.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();select()}};svg.append(g);
 }
 $('city-map').replaceChildren(svg);if(!atlas.registros.length)empty($('map-details'),'Nenhum local neste mapa. O mestre pode adicionar distritos e pontos, anotando o que será compartilhado.');mapZoom();
}
function mapZoom(){const svg=$('city-map').querySelector('svg');if(svg)svg.style.width=(Number($('map-zoom').value)*100)+'%'}
$('map-zoom').oninput=mapZoom;$('map-view').onchange=()=>loadMap().catch(notify);
$('map-new').onclick=()=>{const r=fresh('local');r.sheet.cartografia={tipo:'local',x:50,y:50,largura:20,altura:20,territorio:''};edit(r)};
$('map-export').onclick=()=>{const view=master()?$('map-view').value:'atual';window.open('/api/mapa/exportar?visao='+view,'_blank','noopener')};

$('map-template').onclick=async()=>{await api('/api/mapa/iniciar',{});await load();await loadMap();notify('Santa Aurora criada como proposta editável. Locais ocultos permanecem exclusivos do mestre.')};
const creationLabels={perfil:'Perfil de criação',geracao:'Geração',experiencia:'Experiência',distribuicao:'Distribuição inicial',predador:'Tipo de predador / não aplicável',ambicao:'Ambição',desejo:'Desejo',senhor:'Senhor / mistério intencional',aparencia:'Aparência e idade humana',perdicao:'Perdição do clã · fonte',detalhe_perdicao:'Manifestação pessoal / preferência alimentar',escolhas_assumidas:'Escolhas padrão propostas para revisão'};
function renderCreation(c){const box=$('creation-editor');box.replaceChildren();if(!c)return;box.append(node('h4','Etapas da criação completa'),node('p','Pacote inicial: Criança da Noite, 12ª/13ª geração, distribuição equilibrada. Escolhas pessoais são propostas. Alterações mecânicas serão conferidas ao salvar.'));
 for(const [key,label] of Object.entries(creationLabels)){const l=node('label',label),input=node(['geracao','experiencia'].includes(key)?'input':'textarea');input.id='c-'+key;input.value=c[key]??'';if(input.tagName==='INPUT')input.type='number';else input.rows=key==='perdicao'?5:2;if(['perfil','distribuicao','experiencia','perdicao'].includes(key))input.readOnly=true;l.append(input);box.append(l)}
 const groups={especializacoes:['Especializações · Habilidade | especialização',Object.entries(c.especializacoes).flatMap(([k,v])=>v.map(t=>k+' | '+t)).join('\n')],poderes:['Poderes · Disciplina | nível | nome | fonte',c.poderes.map(p=>[p.disciplina,p.nivel,p.nome,p.fonte].join(' | ')).join('\n')],vantagens:['Vantagens · Nome | pontos | descrição | fonte',c.vantagens.map(p=>[p.nome,p.pontos,p.descricao,p.fonte].join(' | ')).join('\n')],defeitos:['Defeitos · Nome | pontos | descrição | fonte',c.defeitos.map(p=>[p.nome,p.pontos,p.descricao,p.fonte].join(' | ')).join('\n')],conviccoes:['Convicções e Pilares · convicção | Pilar humano',c.conviccoes.map(p=>p.texto+' | '+p.pilar).join('\n')]};
 for(const [key,[label,value]] of Object.entries(groups)){const l=node('label',label),input=node('textarea');input.id='c-'+key;input.rows=4;input.value=value;l.append(input);box.append(l)}
}
function readCreation(before){const c=structuredClone(before);for(const k of Object.keys(creationLabels))c[k]=['geracao','experiencia'].includes(k)?Number($('c-'+k).value):$('c-'+k).value;
 const lines=k=>$('c-'+k).value.split('\n').filter(t=>t.trim()).map(t=>t.split('|').map(v=>v.trim()));
 c.especializacoes={};for(const [skill,specialty] of lines('especializacoes'))(c.especializacoes[skill]??=[]).push(specialty);
 c.poderes=lines('poderes').map(([disciplina,nivel,nome,fonte])=>({disciplina,nivel:Number(nivel),nome,fonte}));
 for(const key of ['vantagens','defeitos'])c[key]=lines(key).map(([nome,pontos,descricao,fonte])=>({nome,pontos:Number(pontos),descricao,fonte}));
 c.conviccoes=lines('conviccoes').map(([texto,pilar])=>({texto,pilar}));return c;
}

const bookStack=[];let bookEpoch=0;
function rememberBook(){if($('book-results').childNodes.length){bookStack.push([...$('book-results').childNodes]);if(bookStack.length>20)bookStack.shift()}}
function backBook(){bookEpoch++;const previous=bookStack.pop();if(previous)$('book-results').replaceChildren(...previous)}
async function showPage(number,type='impressa'){try{const epoch=++bookEpoch;const context=await api('/api/pagina?numero='+number+'&tipo='+type);if(epoch!==bookEpoch)return;rememberBook();$('book-results').replaceChildren();drawContext(context,$('book-results'));switchTab('biblioteca')}catch(e){notify(e)}}
function bookText(text){const pre=node('pre',undefined,'book-text'),pattern=/p[áa]g(?:ina)?s?\.?\s*(\d+)(?:\s*[–—-]\s*(\d+))?/gi;let start=0,match;
 while((match=pattern.exec(text))){pre.append(document.createTextNode(text.slice(start,match.index)));const first=Number(match[1]),last=match[2]?Number(match[2]):first;const b=button(match[0],()=>showPage(first));b.className='book-reference';b.title='Abrir a página impressa '+first;pre.append(b);if(last>first&&last-first<=30){const details=node('details',undefined,'page-range');details.append(node('summary','Páginas do intervalo'));for(let n=first;n<=last;n++)details.append(button(String(n),()=>showPage(n)));pre.append(details)}start=pattern.lastIndex}
 pre.append(document.createTextNode(text.slice(start)));return pre;
}

$('new-complete').onclick=()=>$('complete-dialog').showModal();
$('complete-form').onsubmit=async e=>{e.preventDefault();try{const result=await api('/api/ficha/completa',{nome:$('complete-name').value,cla:$('complete-clan').value,conceito:$('complete-concept').value});$('complete-dialog').close();await load();switchTab('conversa');review(proposals.find(p=>p.id===result.propostas[0]));}catch(e){notify(e)}};

$('complete-existing').onclick=async()=>{try{const result=await api('/api/ficha/completar',{id:editing.id});$('editor').close();await load();switchTab('conversa');review(proposals.find(p=>p.id===result.propostas[0]));}catch(e){notify(e)}};

let campaignCalendar=null,calendarSelected=null;
function currentMonth(){return new Intl.DateTimeFormat('sv-SE',{timeZone:'America/Sao_Paulo',year:'numeric',month:'2-digit'}).format(new Date())}
$('calendar-month').value=currentMonth();
async function loadCalendar(){
 const month=$('calendar-month').value;if(!month)return;
 campaignCalendar=await api('/api/calendario?mes='+month+'&visao='+(master()?$('calendar-view').value:'atual'));
 $('calendar-label').textContent=campaignCalendar.visao==='mestre'?'Mestre: planejamento, notas e acontecimentos visíveis conforme sua campanha. A data é fictícia e editável.':'Jogadores: apenas itens compartilhados e suas notas pessoais. Prévia do mestre: material liberado a todos.';
 const grid=$('calendar-grid');grid.replaceChildren();for(const day of ['Seg','Ter','Qua','Qui','Sex','Sáb','Dom'])grid.append(node('div',day,'calendar-weekday'));
 for(let i=0;i<campaignCalendar.primeiro_dia;i++)grid.append(node('div',undefined,'calendar-gap'));
 for(let day=1;day<=campaignCalendar.dias;day++){
  const cell=node('div',undefined,'calendar-day'),date=month+'-'+String(day).padStart(2,'0'),select=button(String(day),()=>selectCalendarDay(day),'calendar-number');select.setAttribute('aria-label','Ver dia '+date);cell.append(select);
  for(const event of campaignCalendar.eventos.filter(e=>e.dia===day)){const r=event.registro,b=button(r.name,()=>selectCalendarDay(day),'calendar-event');b.append(node('small',states[r.state]+' · '+types[r.kind]));cell.append(b)}
  grid.append(cell);
 }
 $('calendar-undated').replaceChildren();for(const r of campaignCalendar.sem_data)$('calendar-undated').append(button(r.name,()=>calendarRecord(r,[],true),'card'));
 if(calendarSelected&&calendarSelected<=campaignCalendar.dias)selectCalendarDay(calendarSelected);else $('calendar-detail').replaceChildren();
}
function calendarRecord(r,references=[],undated=false){const panel=node('article',undefined,'card');panel.append(node('h3',r.name),node('p',(r.date||'Sem data')+' · '+states[r.state]+' · '+types[r.kind]),node('p',r.summary),bookText(r.content));
 if(r.master_notes)panel.append(node('h4','Notas do mestre'),node('p',r.master_notes));
 const links=node('div',undefined,'actions');for(const ref of references)links.append(button('Abrir referência: '+ref.nome,()=>{if(master()&&campaignCalendar.visao==='jogadores')$('calendar-detail').replaceChildren(calendarRecord(ref.registro));else edit(ref.registro)}));
 for(const id of r.sources||[])links.append(button('Fonte do livro: '+id,()=>showSource(id)));
 if(!(master()&&campaignCalendar.visao==='jogadores'))links.append(button('Abrir registro e versões',()=>edit(r)));
 panel.append(links);if(undated)$('calendar-detail').replaceChildren(panel);return panel;
}
function selectCalendarDay(day){calendarSelected=day;const date=campaignCalendar.mes+'-'+String(day).padStart(2,'0'),target=$('calendar-detail');target.replaceChildren(node('h3','Noite de '+date));
 const events=campaignCalendar.eventos.filter(e=>e.dia===day);for(const event of events)target.append(calendarRecord(event.registro,event.referencias));
 if(!events.length)target.append(node('p','Nenhum item nesta data.'));
 if(!(master()&&campaignCalendar.visao==='jogadores'))target.append(button(master()?'Agendar sessão nesta data':'Criar nota privada nesta data',()=>{const r=fresh(master()?'sessao':'nota');r.date=date+' · noite';if(!master())r.owners=[user.id];edit(r)},'primary'));
}
function moveCalendar(step){const [year,month]=$('calendar-month').value.split('-').map(Number),date=new Date(year,month-1+step,1,12);$('calendar-month').value=date.getFullYear()+'-'+String(date.getMonth()+1).padStart(2,'0');calendarSelected=null;return loadCalendar()}
$('calendar-prev').onclick=()=>moveCalendar(-1).catch(notify);$('calendar-next').onclick=()=>moveCalendar(1).catch(notify);$('calendar-month').onchange=()=>{calendarSelected=null;loadCalendar().catch(notify)};
$('calendar-view').onchange=()=>loadCalendar().catch(notify);$('calendar-today').onclick=()=>{$('calendar-month').value=currentMonth();calendarSelected=null;loadCalendar().catch(notify)};
$('calendar-export').onclick=()=>window.open('/api/calendario/exportar?mes='+$('calendar-month').value+'&visao='+(master()?$('calendar-view').value:'atual'),'_blank','noopener');
