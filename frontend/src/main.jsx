
import React, {useState} from "react";
import {createRoot} from "react-dom/client";
import "./style.css";

const API="http://localhost:5000";
const imageExt=["png","jpg","jpeg","webp","bmp","tif","tiff"];

function App(){
 const [file,setFile]=useState(null),[result,setResult]=useState(null),[restored,setRestored]=useState(null),[loading,setLoading]=useState(false),[error,setError]=useState("");
 const format=n=>{if(n<1024)return `${n} B`;let i=-1;const u=["KB","MB","GB"];do{n/=1024;i++}while(n>=1024&&i<u.length-1);return `${n.toFixed(2)} ${u[i]}`};
 const compress=async()=>{
  if(!file)return; setLoading(true);setError("");setResult(null);setRestored(null);
  const fd=new FormData();fd.append("file",file);
  try{const r=await fetch(`${API}/api/compress`,{method:"POST",body:fd});const d=await r.json();if(!r.ok)throw Error(d.error);setResult(d)}
  catch(e){setError(e.message)}finally{setLoading(false)}
 };
 const decompress=async()=>{
  if(!result?.compressed_name)return;setLoading(true);setError("");
  try{const r=await fetch(`${API}/api/decompress/${encodeURIComponent(result.job)}/${encodeURIComponent(result.compressed_name)}`,{method:"POST"});const d=await r.json();if(!r.ok)throw Error(d.error);setRestored(d)}
  catch(e){setError(e.message)}finally{setLoading(false)}
 };
 const isImage=file&&imageExt.includes(file.name.split(".").pop().toLowerCase());
 return <main>
  <header><div className="pill">DAA • INTELLIGENT COMPRESSION</div><h1>Compress <span>Smarter.</span></h1>
  <p>Adaptive compression that selects Huffman Coding for general data and format-aware codecs for images.</p></header>
  <section className="card">
   <label className="drop"><input type="file" onChange={e=>setFile(e.target.files[0])}/><div className="icon">↑</div>
    <strong>{file?file.name:"Choose any file"}</strong><small>{file?format(file.size):"TXT • CSV • PDF • XLSX • DOCX • PNG • JPEG • ZIP • more"}</small></label>
   {isImage&&<div className="hint"><b>Image detected.</b> The system will test format-aware image compression and keep the smallest result. Image compression may be lossy; PNG→PNG remains lossless.</div>}
   <button className="primary" disabled={!file||loading} onClick={compress}>{loading?"Processing...":"Analyze & Compress"}</button>
   {error&&<div className="error">{error}</div>}
   {result&&<div className="results"><div className="method"><span>SELECTED METHOD</span><b>{result.method}</b><small>{result.algorithm}</small></div>
    <div className="grid">
     <div><span>Original</span><b>{format(result.original_size)}</b></div><div><span>Compressed</span><b>{format(result.compressed_size)}</b></div>
     <div><span>Space Saved</span><b>{result.space_saved_percent}%</b></div><div><span>Ratio</span><b>{result.compression_ratio}</b></div>
     <div><span>Processing</span><b>{result.processing_time_ms} ms</b></div><div><span>Lossless</span><b>{result.lossless?"YES":"NO"}</b></div>
    </div>
    <p className="note">{result.note}</p>
    <div className="actions"><a href={`${API}/api/download/${encodeURIComponent(result.job)}/${encodeURIComponent(result.compressed_name)}`}>Download Compressed</a>
    {result.lossless&&<button onClick={decompress}>Decompress & Restore</button>}</div>
   </div>}
   {restored&&<div className="restored"><b>✓ Restored exactly</b><p>{restored.restored_name} • {format(restored.restored_size)}</p><a href={`${API}${restored.download}`}>Download Restored File</a></div>}
  </section>
  <section className="cards"><div><b>01</b><h3>Analyze</h3><p>Detect file category before choosing a compression strategy.</p></div>
  <div><b>02</b><h3>Optimize</h3><p>Use Huffman + Min Heap for general data or an image codec for images.</p></div>
  <div><b>03</b><h3>Compare</h3><p>Keep the smaller result instead of blindly compressing everything.</p></div></section>
  <footer>Huffman • Greedy • Min Heap • Adaptive Compression</footer>
 </main>
}
createRoot(document.getElementById("root")).render(<App/>);
