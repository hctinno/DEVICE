'use strict';
const fs=require('node:fs'),path=require('node:path'),{randomUUID}=require('node:crypto');
function development(root){
 for(let current=path.resolve(root);;current=path.dirname(current)){
  if(path.basename(current)==='development'&&path.basename(path.dirname(current))==='.local'){
   const file=path.join(current,'layout.json'),info=fs.lstatSync(file);
   if(!info.isFile()||info.isSymbolicLink()||info.nlink!==1||info.size>1048576)throw Error('managed_layout_invalid');
   const value=JSON.parse(fs.readFileSync(file,'utf8').replace(/^\uFEFF/,''));
   const keys=['control_root','directories','path_aliases','project_root_relative','schema_version','workspaces'];
   const kinds=['archive','integration','runs','toolchains','workspaces'];
   if(JSON.stringify(Object.keys(value).sort())!==JSON.stringify(keys)||value.schema_version!==1||
      value.project_root_relative!=='../..'||value.control_root!=='runs/control/DGMAutoLab'||
      !Array.isArray(value.workspaces)||!Array.isArray(value.path_aliases)||
      !value.directories||JSON.stringify(Object.keys(value.directories).sort())!==JSON.stringify(kinds)||
      !kinds.every(kind=>value.directories[kind]===kind))throw Error('managed_layout_invalid');
   for(let node=current;;node=path.dirname(node)){
    if(fs.lstatSync(node).isSymbolicLink())throw Error('managed_layout_reparse');
    if(path.dirname(node)===node)break;
   }
   return current;
  }
  if(path.dirname(current)===current)break;
 }
 throw Error('managed_ancestor_missing');
}
function python(root){return path.join(development(root),'toolchains/python',process.platform==='win32'?'Scripts/python.exe':'bin/python');}
function stage(root){
 const target=path.resolve(root),runs=path.join(development(root),'runs'),relative=path.relative(runs,target);
 if(!relative||relative==='..'||relative.startsWith('..'+path.sep)||path.isAbsolute(relative))throw Error('managed_browser_stage_required');
 return target;
}
function output(root,name){
 if(typeof name!=='string'||!/^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$/.test(name))throw Error('managed_output_name_invalid');
 return path.join(development(root),'runs/browser-checks',name+'-'+randomUUID());
}
module.exports={python,output,stage};
