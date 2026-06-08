# Integrating LLM-based data mining with X-ray diffraction-driven machine learning for closed-loop discovery of oxygen carriers in chemical looping

This project integrates **large language model (LLM)-based literature data mining** with **X-ray diffraction (XRD)-driven machine learning** for the discovery of oxygen carriers in chemical looping systems.

The main objective of this project is to automatically extract structured information from experimental literature on chemical looping oxygen carriers. An open-source **Qwen3.5-9B** multimodal large language model is locally deployed using llama.cpp on a single NVIDIA RTX 4090 GPU. The model is used to analyze both full-text content and page-by-page images converted from PDF papers, enabling the identification of characterization figures and the extraction of key information from the literature.

The extracted information mainly includes characterization figure types, figure numbers, and corresponding material names. These results are further organized and checked to construct a **first-ever integrated “XRD–TGA” comprehensive experimental dataset** for OCs. Based on the constructed dataset, machine learning models are developed to predict oxygen carrier properties from XRD patterns.

## File Description

* **`XRD-capacity.xlsx`**: Source dataset used for machine learning model training, containing XRD pattern features and the corresponding oxygen release capacity data.
* **`XRD-T.xlsx`**: Source dataset used for machine learning model training, containing XRD pattern features and the corresponding reduction temperature data.
* **`data mining results.xlsx`**: Summary file of the LLM-based literature data mining results, including XRD and TGA figure number obtained from image-based input, text-based input, and the manually verified actual figure numbers reported in the literature.
* **`Machine learning model/`**: Folder containing the codes for machine learning model construction and optimization, including 1D-CNN and Transformer models based on XRD pattern features.
* **`LLM data-mining code/`**: Folder containing the codes for converting PDF literature into text and images, as well as the codes for calling the locally deployed LLM to perform literature data mining using text and image inputs, respectively.
* **`LLM data-mining result/`**: Folder containing the literature text-mining results, including full-text files and LLM-based data mining results from both image and text inputs.

## Local LLM Deployment

The LLM inference environment is built on a local Linux server. The llama.cpp framework is compiled with CUDA support and used as the backend inference engine for the Qwen3.5-9B multimodal model. The model is deployed on a single NVIDIA RTX 4090 GPU, allowing local and batch processing of literature text and page images without relying on external cloud-based APIs.
The local deployment provides the following advantages:
* Fully local processing of literature data and characterization images.
* Reduced dependence on commercial or remote LLM services.
* Flexible control over inference parameters and batch-processing workflows.

## Machine Learning Models

The machine learning part of this project focuses on learning the relationship between XRD patterns and oxygen carrier properties. The model code/ folder contains implementations of 1D-CNN and Transformer models, which use XRD patterns as structural descriptors to predict oxygen release capacity and reduction temperature.

This XRD-driven modeling strategy provides a data-driven route for evaluating oxygen carrier performance based on experimentally available characterization data.

## Workflow

The overall workflow of this project consists of four main steps.

First, experimental literature related to chemical looping oxygen carriers is collected and converted into full-text files and page-by-page images using `PDF convert to text and images.py`.

Second, `text analysis by LLM.py` and `image analysis by LLM.py` are used to extract characterization pattern information from the literature. The former takes full-text content as input, while the latter takes page images as input. This dual-input strategy enables the identification of characterization figures such as XRD, TGA, DTG, TPR, and TPD, together with their figure numbers and corresponding materials.

Third, the LLM-generated results are organized and checked to construct a structured dataset containing the figure number information of XRD and TGA characterization patterns. The identified characterization patterns are then digitized, structured, and processed for feature extraction using digitization software, resulting in the final machine learning datasets, `XRD-capacity.xlsx` and `XRD-T.xlsx`.

Finally, based on `XRD-capacity.xlsx` and **`XRD-T.xlsx`, machine learning models in the `Machine learning model/` folder are trained to predict key oxygen carrier properties, including oxygen release capacity and reduction temperature.

## Purpose

This project provides an automated workflow for high-throughput literature data mining, material dataset construction, and machine learning-based property prediction for chemical looping oxygen carriers. By combining multimodal large language models with XRD-driven machine learning methods, this project reduces the workload of manual literature extraction and provides data and model support for the rapid screening and performance prediction of oxygen carrier materials. Overall, this integrated framework offers a new pathway for the data-driven development and discovery of oxygen carriers in chemical looping systems.
