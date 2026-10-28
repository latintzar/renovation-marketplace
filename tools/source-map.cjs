const fs=require('node:fs'),path=require('node:path');
const root=path.resolve(__dirname,'..');
const ts=require(path.join(root,'apps/scope/product/web/node_modules/typescript'));
const out=[];
function walk(dir){for(const item of fs.readdirSync(dir,{withFileTypes:true})){const p=path.join(dir,item.name);if(item.isDirectory())walk(p);else if(/\.(tsx?|jsx?)$/.test(item.name)){const text=fs.readFileSync(p,'utf8'),source=ts.createSourceFile(p,text,ts.ScriptTarget.Latest,true);function visit(n){let name=null;if(ts.isFunctionDeclaration(n)&&n.name)name=n.name.getText(source);else if(ts.isMethodDeclaration(n)&&n.name)name=n.name.getText(source);else if(ts.isVariableDeclaration(n)&&n.initializer&&(ts.isArrowFunction(n.initializer)||ts.isFunctionExpression(n.initializer))){name=n.name.getText(source);n=n.initializer;}if(name){const doc=(ts.getJSDocCommentsAndTags(n)||[]).map(x=>typeof x.comment==='string'?x.comment:'').filter(Boolean).join(' ').split(/\n\s*\n/)[0].replace(/\s+/g,' ').slice(0,400);out.push({language:'TypeScript',file:path.relative(root,p),name,line:source.getLineAndCharacterOfPosition(n.getStart(source)).line+1,arguments:(n.parameters||[]).map(x=>x.name.getText(source)),description:doc});}ts.forEachChild(n,visit);}visit(source);}}}
walk(path.join(root,'apps/scope/product/web/src'));
walk(path.join(root,'packages/ui/src'));
walk(path.join(root,'packages/brand/src'));
process.stdout.write(JSON.stringify(out));
