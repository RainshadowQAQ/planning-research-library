import {mkdir,cp} from 'node:fs/promises';
await mkdir('web/vendor/pdfjs',{recursive:true});
for(const name of ['build','web','cmaps','standard_fonts','wasm','iccs','LICENSE']){
 await cp('node_modules/pdfjs-dist/'+name,'web/vendor/pdfjs/'+name,{recursive:true});
}
