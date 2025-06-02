# pdftools
Small set of useful pdf tools using python/bash script

- [pdfcropy.py](https://github.com/usernaamee/pdftools/blob/main/pdfcrop.py): crop pdf pages to specified width and height values, taking reference from center of the pdf (center crop)
- [pdftoccopy.py](https://github.com/usernaamee/pdftools/blob/main/pdftoccopy.py): copy table of contents from one pdf to another pdf
- [pdfmanip.py](https://github.com/usernaamee/pdftools/blob/main/pdfmanip.py): pdf manipulation tool: extract, cut, paste, merge

## pdfmanip.py usage
- Extract selected pages from a pdf file:  
  `python pdf_tool.py extract input.pdf output_extracted.pdf -r "1-3,5,end"`
- Remove selected pages from a pdf file:  
  `python pdf_tool.py cut input.pdf output_cut.pdf -r "2,4-6"`
- Paste one pdf inside another pdf file:  
  `python pdf_tool.py paste target.pdf source.pdf output_pasted.pdf -at 3`
- Split a pdf into individual pages:  
  `python pdf_tool.py split input.pdf output_directory/`
- Merge multiple pdf files into one:  
  `python pdf_tool.py merge merged_output.pdf input1.pdf input2.pdf input3.pdf`
