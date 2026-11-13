import pypdf, io, pathlib
out = pathlib.Path('public/sample_files')
out.mkdir(parents=True, exist_ok=True)
writer = pypdf.PdfWriter()
writer.add_blank_page(width=612, height=792)
buf = io.BytesIO()
writer.write(buf)
(out/'cse_dsa_balanced_trees_graphs_notes.pdf').write_bytes(buf.getvalue())
print('dummy pdf created')