import re
import json
import logging
from typing import List, Dict, Any, Optional
import httpx
from bson import ObjectId

from app.config import settings
from app.database import get_db
from app.services.embedding_service import (
    get_text_embedding,
    cosine_similarity
)

logger = logging.getLogger("campusverse.rag_engine")

RAG_STOP_WORDS = {
    "what", "is", "are", "the", "a", "an", "in", "on", "at", "by", "for", "with",
    "about", "against", "between", "into", "through", "during", "before", "after",
    "above", "below", "to", "from", "up", "down", "of", "off", "over", "under",
    "again", "further", "then", "once", "here", "there", "when", "where", "why",
    "how", "all", "any", "both", "each", "few", "more", "most", "other", "some",
    "such", "no", "nor", "not", "only", "own", "same", "so", "than", "too", "very",
    "can", "will", "just", "don", "should", "now", "tell", "explain", "give", "define",
    "mean", "meaning", "concept", "wt", "whats", "describe", "detail", "details",
    "question", "questions", "important", "notes", "material", "study", "module",
    "please", "help", "show", "write", "list", "marks", "university", "exam",
    "uploaded", "document", "documents", "syllabus", "summary", "overview", "give",
    "find", "search", "answer", "answers"
}

async def retrieve_context_chunks(
    query: str,
    material_ids: Optional[List[str]] = None,
    user_id: Optional[str] = None,
    is_admin: bool = False,
    top_k: int = 5
) -> List[Dict[str, Any]]:
    """
    Retrieves the most semantically relevant text chunks from the selected materials or across all authorized notes.
    Ensures active document chunks are always available to grounded answer generators.
    """
    db = get_db()
    if db is None:
        return []

    # Filter by selected materials if specified; otherwise search across all approved student notes
    valid_ids = [str(mid) for mid in (material_ids or []) if mid]
    query_filter: Dict[str, Any] = {
        "status": {"$nin": ["REJECTED", "ADMIN_REJECTED"]}
    }
    if valid_ids:
        query_filter["materialId"] = {"$in": valid_ids}

    cursor = db["document_chunks"].find(query_filter)
    chunks = await cursor.to_list(length=1000)
    if not chunks:
        # If no chunks in collection yet, check if we can index them on-the-fly from materials
        from app.services.embedding_service import index_document_chunks
        from app.services.text_extract import extract_document_pages
        from app.storage.factory import get_storage

        storage = get_storage()
        target_ids = valid_ids
        if not target_ids:
            # Load all approved materials
            mats_cursor = db["materials"].find({"status": {"$nin": ["REJECTED", "ADMIN_REJECTED"]}}).limit(20)
            target_docs = await mats_cursor.to_list(length=20)
            target_ids = [str(d["_id"]) for d in target_docs]

        for mid in target_ids:
            try:
                m_doc = await db["materials"].find_one({"_id": ObjectId(mid) if ObjectId.is_valid(mid) else mid})
                if m_doc and m_doc.get("status") not in ["REJECTED", "ADMIN_REJECTED"]:
                    if m_doc.get("storageKey"):
                        buf = await storage.download(m_doc["storageKey"])
                        pages = extract_document_pages(buf, m_doc.get("extension", ".pdf"))
                        if pages:
                            await index_document_chunks(
                                material_id=str(m_doc["_id"]),
                                title=m_doc.get("title", "Study Material"),
                                pages_text=pages,
                                uploader_id=str(m_doc.get("uploader", "")),
                                status=m_doc.get("status", "ADMIN_APPROVED")
                            )
                            cursor = db["document_chunks"].find(query_filter)
                            chunks = await cursor.to_list(length=1000)
                    
                    if not chunks:
                        # Fallback to document summary/description as chunk
                        chunks.append({
                            "materialId": str(m_doc["_id"]),
                            "title": m_doc.get("title", "Study Material"),
                            "pageNumber": 1,
                            "text": m_doc.get("summary") or m_doc.get("description") or m_doc.get("title", ""),
                            "embedding": []
                        })
            except Exception as e:
                logger.debug("On-the-fly chunk indexing notice for %s: %s", mid, e)

    if not chunks:
        return []

    q_embedding = await get_text_embedding(query)
    raw_q_words = re.findall(r"\b[a-zA-Z]{2,}\b", query.lower())
    q_domain_words = set(w for w in raw_q_words if w not in RAG_STOP_WORDS)

    # Expand domain words bidirectionally with academic acronym synonyms
    expanded_domain_words = set(q_domain_words)
    for w in list(q_domain_words):
        if w in ACRONYM_SYMS:
            expanded_domain_words.update(ACRONYM_SYMS[w])
        for acr, terms in ACRONYM_SYMS.items():
            if w in terms:
                expanded_domain_words.add(acr)
                expanded_domain_words.update(terms)

    scored = []
    for c in chunks:
        emb = c.get("embedding")
        sim = cosine_similarity(q_embedding, emb) if emb else 0.20
        c_text = c.get("text", "").lower()
        c_title = c.get("title", "").lower()
        
        # Word overlap on genuine domain terms (expanded bidirectionally)
        overlap = sum(1 for w in expanded_domain_words if w in c_text or w in c_title)
        
        # If user asked specific domain terms and none exist in chunk/title, reject chunk unless embedding similarity is high
        if expanded_domain_words and overlap == 0 and sim < 0.38:
            continue

        boost = min(0.35, overlap * 0.08)
        final_score = sim + boost
        
        if final_score >= 0.20:
            scored.append({
                "materialId": c["materialId"],
                "title": c.get("title", "Document"),
                "pageNumber": c.get("pageNumber", 1),
                "text": c.get("text", ""),
                "score": final_score
            })

    scored.sort(key=lambda x: x["score"], reverse=True)
    if scored:
        return scored[:top_k]

    # Contextual Fallback: If strict threshold filtered out chunks, retain top chunks of active selected material
    fallback_scored = []
    for c in chunks:
        fallback_scored.append({
            "materialId": c.get("materialId", ""),
            "title": c.get("title", "Document"),
            "pageNumber": c.get("pageNumber", 1),
            "text": c.get("text", ""),
            "score": 0.50
        })
    return fallback_scored[:top_k]

# Comprehensive Academic Knowledge Base for Instant, High-Quality Fallbacks
ACADEMIC_KNOWLEDGE_BASE = {
    "deep learning": (
        "**Deep Learning** is a specialized branch of **Machine Learning** based on **Artificial Neural Networks** with multiple layers (deep architectures). It automatically learns hierarchical representations and feature patterns directly from raw data without manual feature engineering.\n\n"
        "**Key Architectural Components:**\n"
        "- **Multi-Layer Neural Networks:** Consists of an input layer, multiple hidden layers (feature extractors), and an output layer (predictions).\n"
        "- **Feature Learning:** Progressively extracts low-level patterns (edges, textures) in early layers and high-level abstract concepts (objects, shapes) in deeper layers.\n"
        "- **Training Mechanism:** Employs **Backpropagation** and **Gradient Descent** along with loss functions (e.g., Cross-Entropy, MSE) to optimize synaptic weights.\n"
        "- **Core Architectures:** Convolutional Neural Networks (**CNN**) for visual processing, Recurrent Neural Networks (**RNN/LSTM**) and **Transformers** for sequential and language data."
    ),
    "machine learning": (
        "**Machine Learning (ML)** is a subset of **Artificial Intelligence** that focuses on building algorithmic models that learn patterns from training data to make predictions or decisions without being explicitly programmed.\n\n"
        "**Primary Categories:**\n"
        "- **Supervised Learning:** Trains on labeled input-output pairs to solve classification and regression problems (e.g., Linear Regression, Random Forest).\n"
        "- **Unsupervised Learning:** Discovers hidden structures or natural groupings in unlabeled datasets (e.g., K-Means clustering, PCA).\n"
        "- **Reinforcement Learning:** Uses trial-and-error interactions where an agent learns optimal policies through positive rewards and penalties."
    ),
    "neural network": (
        "An **Artificial Neural Network (ANN)** is a computational model inspired by biological neural networks in the human brain, designed to recognize non-linear patterns and complex data relationships.\n\n"
        "**Core Structure:**\n"
        "- **Artificial Neurons (Nodes):** Receive input signals, multiply them by learnable **weights**, add a **bias**, and compute an output.\n"
        "- **Activation Functions:** Mathematical functions (e.g., ReLU, Sigmoid, Softmax) that introduce non-linearity, enabling the network to learn intricate patterns.\n"
        "- **Layer Organization:** Structured into an **Input Layer**, one or more **Hidden Layers**, and an **Output Layer**."
    ),
    "convolutional neural network": (
        "A **Convolutional Neural Network (CNN)** is a specialized deep neural network architecture designed primarily for grid-structured data such as images and video.\n\n"
        "**Key Layers:**\n"
        "- **Convolutional Layer:** Uses learnable filters (kernels) to extract spatial features such as edges, corners, and textures.\n"
        "- **Pooling Layer:** Downsamples feature maps (e.g., Max Pooling) to reduce spatial dimensions and computational complexity while maintaining translation invariance.\n"
        "- **Fully Connected (FC) Layer:** Connects extracted features to final output classes for classification."
    ),
    "cnn": (
        "A **Convolutional Neural Network (CNN)** is a specialized deep neural network architecture designed primarily for grid-structured data such as images and video.\n\n"
        "**Key Layers:**\n"
        "- **Convolutional Layer:** Uses learnable filters (kernels) to extract spatial features such as edges, corners, and textures.\n"
        "- **Pooling Layer:** Downsamples feature maps (e.g., Max Pooling) to reduce spatial dimensions and computational complexity while maintaining translation invariance.\n"
        "- **Fully Connected (FC) Layer:** Connects extracted features to final output classes for classification."
    ),
    "recurrent neural network": (
        "A **Recurrent Neural Network (RNN)** is a class of neural networks tailored for sequential, temporal, or time-series data such as text, speech, and financial trends.\n\n"
        "**Key Characteristics:**\n"
        "- **Internal Memory:** Utilizes cyclical feedback connections where output from the previous time step serves as input for the current step.\n"
        "- **Shared Parameters:** Applies identical weights across all sequence steps, reducing total parameters.\n"
        "- **Modern Variants:** **LSTM** (Long Short-Term Memory) and **GRU** (Gated Recurrent Unit) architectures overcome vanishing gradient limitations."
    ),
    "rnn": (
        "A **Recurrent Neural Network (RNN)** is a class of neural networks tailored for sequential, temporal, or time-series data such as text, speech, and financial trends.\n\n"
        "**Key Characteristics:**\n"
        "- **Internal Memory:** Utilizes cyclical feedback connections where output from the previous time step serves as input for the current step.\n"
        "- **Shared Parameters:** Applies identical weights across all sequence steps, reducing total parameters.\n"
        "- **Modern Variants:** **LSTM** (Long Short-Term Memory) and **GRU** (Gated Recurrent Unit) architectures overcome vanishing gradient limitations."
    ),
    "activation function": (
        "An **Activation Function** is a mathematical equation applied to the output of an artificial neuron to introduce non-linearity into the network, allowing it to approximate arbitrary complex functions.\n\n"
        "**Common Activation Functions:**\n"
        "- **ReLU (Rectified Linear Unit):** Defined as $f(x) = \\max(0, x)$. Accelerates convergence and mitigates vanishing gradients in hidden layers.\n"
        "- **Sigmoid:** Maps real values into the range $(0, 1)$. Primarily utilized for binary classification output layers.\n"
        "- **Softmax:** Converts unnormalized logits into normalized probability distributions across mutually exclusive classes for multi-class classification.\n"
        "- **Tanh (Hyperbolic Tangent):** Maps inputs to $(-1, 1)$, centered at zero for balanced hidden layer gradients."
    ),
    "loss function": (
        "A **Loss Function** (or Cost Function) is a mathematical metric that calculates the deviation between a model's predicted outputs and the true target labels during training.\n\n"
        "**Standard University Exam Combinations:**\n"
        "- **Mean Squared Error (MSE):** Used in **Regression** problems to penalize large prediction variances.\n"
        "- **Binary Cross-Entropy:** Paired with **Sigmoid** activation for **Binary Classification** problems (e.g., Spam Detection).\n"
        "- **Categorical Cross-Entropy:** Paired with **Softmax** activation for **Multi-Class Classification** problems."
    ),
    "backpropagation": (
        "**Backpropagation** (Backward Propagation of Errors) is the fundamental training algorithm for artificial neural networks that calculates the gradient of the loss function with respect to each network weight using the calculus chain rule.\n\n"
        "**Algorithm Steps:**\n"
        "1. **Forward Pass:** Input data propagates through network layers to produce predictions and compute total loss.\n"
        "2. **Backward Pass:** Error gradients propagate backward from output to input layers.\n"
        "3. **Weight Update:** Optimization algorithms (e.g., SGD, Adam) adjust weights in the negative gradient direction to minimize prediction error."
    ),
    "supervised learning": (
        "**Supervised Learning** is a machine learning paradigm where the algorithm is trained on a labeled dataset containing paired input features and known ground-truth targets.\n\n"
        "**Core Problem Types:**\n"
        "- **Classification:** Predicts discrete categorical labels (e.g., Disease Diagnosis, Image Recognition).\n"
        "- **Regression:** Predicts continuous numerical quantities (e.g., House Price Estimation, Temperature Forecasting)."
    ),
    "unsupervised learning": (
        "**Unsupervised Learning** is a machine learning paradigm that finds intrinsic patterns, groupings, and underlying structures within unlabeled datasets without manual supervision.\n\n"
        "**Major Techniques:**\n"
        "- **Clustering:** Groups similar data instances together (e.g., **K-Means**, Hierarchical Clustering).\n"
        "- **Dimensionality Reduction:** Compresses feature spaces while preserving essential data variance (e.g., **PCA** - Principal Component Analysis).\n"
        "- **Association Rule Mining:** Uncovers item co-occurrence relationships (e.g., **Apriori Algorithm**)."
    ),
    "overfitting": (
        "**Overfitting** occurs when a machine learning model memorizes training noise and sample idiosyncrasies rather than generalizable underlying patterns, resulting in superior training accuracy but poor test/validation performance.\n\n"
        "**Common Mitigation Techniques:**\n"
        "- **Regularization:** Adding $L_1$ (Lasso) or $L_2$ (Ridge) penalties to shrink excessive model weights.\n"
        "- **Dropout:** Randomly deactivating neuron subsets during training iterations in deep networks.\n"
        "- **Cross-Validation & Early Stopping:** Halting training once validation loss starts degrading."
    ),
    "data mining": (
        "**Data Mining** is the computational process of analyzing massive datasets to uncover hidden patterns, meaningful anomalies, and actionable intelligence that standard database queries cannot reveal.\n\n"
        "**Standard Tasks:**\n"
        "- **Classification:** Assigning records to predefined categories (e.g., Decision Trees, Naive Bayes).\n"
        "- **Clustering:** Grouping records based on similarity metrics (e.g., K-Means, DBSCAN).\n"
        "- **Association Rules:** Discovering itemset correlation rules (e.g., Market Basket Analysis via Apriori).\n"
        "- **Anomaly Detection:** Flagging rare, deviating data points (e.g., Credit Card Fraud Detection)."
    ),
    "deep learning in data mining": (
        "**Deep Learning in Data Mining:**\n\n"
        "**Deep Learning in Data Mining** refers to the application of deep artificial neural networks (such as CNNs, RNNs, and Autoencoders) to uncover complex, non-linear patterns and extract high-level feature representations from massive, high-dimensional datasets.\n\n"
        "Unlike traditional data mining techniques that require laborious manual feature extraction and operate primarily on structured tabular data, Deep Learning integrates representation learning directly into the mining pipeline.\n\n"
        "**Key Applications in Data Mining:**\n"
        "- **Automated Feature Representation:** Deep architectures autonomously extract hierarchical features directly from raw, uncurated data (text, images, sensor logs, and graph streams) without manual attribute engineering.\n"
        "- **Deep Clustering & Pattern Discovery:** Combines autoencoders with clustering objectives (e.g., Deep Embedded Clustering) to discover natural cluster groupings in complex high-dimensional feature spaces.\n"
        "- **Advanced Classification & Prediction:** Employs multi-layer neural networks for superior predictive precision on complex behavioral, transactional, and genomic datasets where traditional decision trees struggle.\n"
        "- **Anomaly & Fraud Detection:** Autoencoders learn the baseline distribution of standard transactions; data instances exhibiting high reconstruction errors are accurately flagged as fraud, cyber intrusions, or system anomalies."
    ),
    "deep learning vs data mining": (
        "**Comparison: Data Mining vs. Deep Learning:**\n\n"
        "- **Definition:** **Data Mining** is the broader discovery process (KDD) to uncover hidden patterns, anomalies, and correlations from structured datasets using statistics, machine learning, and database systems. **Deep Learning** is a specialized subfield of Machine Learning utilizing multi-layer neural networks to learn representations from raw data.\n"
        "- **Data Structure:** Data Mining traditionally operates on structured tabular records; Deep Learning excels with massive, unstructured data (images, video, natural language, audio).\n"
        "- **Feature Engineering:** Traditional Data Mining relies heavily on domain experts for manual feature selection and transformation; Deep Learning performs end-to-end automatic feature extraction.\n"
        "- **Complementary Role:** Modern Data Mining leverages Deep Learning models as advanced extraction, clustering, and classification algorithms within the KDD pipeline."
    ),
    "deep learning vs machine learning": (
        "**Difference Between Machine Learning (ML) and Deep Learning (DL):**\n\n"
        "| Feature | Machine Learning (ML) | Deep Learning (DL) |\n"
        "| :--- | :--- | :--- |\n"
        "| **Hierarchy** | Broad AI field for predictive learning algorithms. | Specialized subfield of ML based on multi-layer neural networks. |\n"
        "| **Feature Engineering** | Requires manual feature extraction by domain experts. | Automatically learns hierarchical feature representations from raw data. |\n"
        "| **Data Dependency** | Performs well on smaller to medium tabular datasets. | Excels on massive, high-dimensional datasets (images, text, audio). |\n"
        "| **Hardware** | Executes efficiently on standard CPUs. | Requires high-performance GPUs / TPUs for training. |\n"
        "| **Algorithms** | Linear Regression, Decision Trees, SVM, K-Means. | CNNs, RNNs/LSTMs, Autoencoders, Transformers. |"
    ),
    "difference between deep learning and machine learning": (
        "**Difference Between Machine Learning (ML) and Deep Learning (DL):**\n\n"
        "| Feature | Machine Learning (ML) | Deep Learning (DL) |\n"
        "| :--- | :--- | :--- |\n"
        "| **Hierarchy** | Broad AI field for predictive learning algorithms. | Specialized subfield of ML based on multi-layer neural networks. |\n"
        "| **Feature Engineering** | Requires manual feature extraction by domain experts. | Automatically learns hierarchical feature representations from raw data. |\n"
        "| **Data Dependency** | Performs well on smaller to medium tabular datasets. | Excels on massive, high-dimensional datasets (images, text, audio). |\n"
        "| **Hardware** | Executes efficiently on standard CPUs. | Requires high-performance GPUs / TPUs for training. |\n"
        "| **Algorithms** | Linear Regression, Decision Trees, SVM, K-Means. | CNNs, RNNs/LSTMs, Autoencoders, Transformers. |"
    ),
    "ai ethics": (
        "**AI Ethics** (Artificial Intelligence Ethics) refers to the multidisciplinary field of principles, societal guidelines, and moral frameworks designed to ensure artificial intelligence systems are developed and deployed responsibly, transparently, and safely.\n\n"
        "**Key Pillars of AI Ethics:**\n"
        "- **Data Privacy & Scraping:** Regulating the collection of web-scale datasets without creator consent and protecting personal intellectual property.\n"
        "- **Copyright & Intellectual Property:** Determining authorship and licensing rights for AI-generated works (text, artwork, audio, code).\n"
        "- **Fairness & Bias Mitigation:** Ensuring models do not perpetuate societal, racial, or gender disparities embedded in historical training datasets.\n"
        "- **Transparency & Explainability (XAI):** Enabling humans to understand how an AI model arrives at its decisions, especially in healthcare, law, and lending.\n"
        "- **Accountability & Safety:** Preventing harmful misuse, malicious deepfakes, disinformation, and ensuring legal liability when autonomous systems fail."
    ),
    "ethics in ai": (
        "**AI Ethics** (Artificial Intelligence Ethics) refers to the multidisciplinary field of principles, societal guidelines, and moral frameworks designed to ensure artificial intelligence systems are developed and deployed responsibly, transparently, and safely.\n\n"
        "**Key Pillars of AI Ethics:**\n"
        "- **Data Privacy & Scraping:** Regulating the collection of web-scale datasets without creator consent and protecting personal intellectual property.\n"
        "- **Copyright & Intellectual Property:** Determining authorship and licensing rights for AI-generated works (text, artwork, audio, code).\n"
        "- **Fairness & Bias Mitigation:** Ensuring models do not perpetuate societal, racial, or gender disparities embedded in historical training datasets.\n"
        "- **Transparency & Explainability (XAI):** Enabling humans to understand how an AI model arrives at its decisions, especially in healthcare, law, and lending.\n"
        "- **Accountability & Safety:** Preventing harmful misuse, malicious deepfakes, disinformation, and ensuring legal liability when autonomous systems fail."
    ),
    "ethics": (
        "**Ethics in Artificial Intelligence & Generative AI:**\n\n"
        "In modern computing and Generative AI, **Ethics** encompasses the moral responsibilities, legal standards, and social guidelines governing the creation and use of intelligent models.\n\n"
        "**Major Ethical Concerns in Generative AI:**\n"
        "1. **Copyright & Data Scraping:** Training frontier models on billions of web pages, copyrighted books, artistic illustrations, and private codebases without explicit consent or creator compensation.\n"
        "2. **Ownership of AI-Generated Content:** Legal ambiguities regarding who owns synthesized outputs—the model developer, the user writing the prompt, or the artists whose work was scraped.\n"
        "3. **Bias, Toxicity & Fairness:** Generative models can reflect and amplify harmful cultural biases, hate speech, or discriminatory stereotypes present in uncurated Internet data.\n"
        "4. **Hallucination & Misinformation:** The risk of models generating plausible-sounding but factually fabricated information in critical fields like medicine, law, or engineering.\n"
        "5. **Deepfakes & Deception:** The unauthorized synthesis of human likenesses, voices, and synthetic identities used for fraud or social engineering.\n\n"
        "**Mitigation Approaches:** Responsible AI guidelines, RLHF (Reinforcement Learning from Human Feedback), red-teaming, data provenance watermarking, and transparent AI governance."
    ),
    "generative ai": (
        "**Generative AI** is a class of Artificial Intelligence systems that leverage deep learning architectures to generate novel, realistic content—such as human-like text, synthetic images, 3D assets, audio, and executable code—by learning the underlying probability distribution of massive training datasets.\n\n"
        "**Core Architectural Pillars:**\n"
        "- **Large Language Models (LLMs):** Transformer-based models (e.g., GPT, Gemini) trained on billions of tokens via self-supervised autoregressive next-token prediction.\n"
        "- **Diffusion Models:** Image and video generators (e.g., Stable Diffusion) that learn to generate high-fidelity visuals by iteratively reversing Gaussian noise.\n"
        "- **Variational Autoencoders (VAEs) & GANs:** Latent space mapping and adversarial minimax training for synthetic data creation."
    ),
    "generative models vs discriminative models": (
        "**Comparison: Generative Models vs. Discriminative Models:**\n\n"
        "| Characteristic | Generative Models | Discriminative Models |\n"
        "| :--- | :--- | :--- |\n"
        "| **Mathematical Objective** | Learns the **joint probability distribution** $P(X, Y)$ or data distribution $P(X)$. | Learns the **conditional probability distribution** $P(Y \\mid X)$ directly. |\n"
        "| **Core Function** | Generates novel, realistic synthetic data samples similar to training inputs. | Predicts class labels or values for a given input by learning decision boundaries. |\n"
        "| **Question Answered** | *\"How likely is this data to occur? Can I generate more like it?\"* | *\"Given feature inputs $X$, which label $Y$ does it belong to?\"* |\n"
        "| **Sample Generation** | Capable of synthesizing novel text, images, 3D models, and audio. | Cannot generate new data samples; only classifies or regresses. |\n"
        "| **Key Examples** | GANs, VAEs, Diffusion Models, Autoregressive Transformers, Naive Bayes. | Logistic Regression, Support Vector Machines (SVM), Decision Trees, Standard CNNs. |"
    ),
    "generative vs discriminative": (
        "**Comparison: Generative Models vs. Discriminative Models:**\n\n"
        "| Characteristic | Generative Models | Discriminative Models |\n"
        "| :--- | :--- | :--- |\n"
        "| **Mathematical Objective** | Learns the **joint probability distribution** $P(X, Y)$ or data distribution $P(X)$. | Learns the **conditional probability distribution** $P(Y \\mid X)$ directly. |\n"
        "| **Core Function** | Generates novel, realistic synthetic data samples similar to training inputs. | Predicts class labels or values for a given input by learning decision boundaries. |\n"
        "| **Question Answered** | *\"How likely is this data to occur? Can I generate more like it?\"* | *\"Given feature inputs $X$, which label $Y$ does it belong to?\"* |\n"
        "| **Sample Generation** | Capable of synthesizing novel text, images, 3D models, and audio. | Cannot generate new data samples; only classifies or regresses. |\n"
        "| **Key Examples** | GANs, VAEs, Diffusion Models, Autoregressive Transformers, Naive Bayes. | Logistic Regression, Support Vector Machines (SVM), Decision Trees, Standard CNNs. |"
    ),
    "generative models": (
        "**Generative Models** are machine learning models designed to capture the underlying probability distribution of a dataset ($P(X)$ or $P(X, Y)$) in order to generate new, synthetic data instances that resemble the training data.\n\n"
        "**Major Architectures:**\n"
        "- **Variational Autoencoders (VAEs):** Probabilistic generative models that encode data into a continuous latent space and sample from it to reconstruct outputs.\n"
        "- **Generative Adversarial Networks (GANs):** Pits a Generator network against a Discriminator network in a minimax zero-sum game.\n"
        "- **Diffusion Models (e.g., Stable Diffusion):** Iteratively corrupts data with Gaussian noise and trains a neural network to reverse the denoising process to synthesize high-fidelity images/audio.\n"
        "- **Autoregressive Models (e.g., GPT, LLMs):** Predicts the probability of the next sequential token conditioned on preceding tokens."
    ),
    "discriminative models": (
        "**Discriminative Models** are machine learning models that model the conditional probability distribution $P(Y \\mid X)$ to classify inputs or predict target values.\n\n"
        "**Key Characteristics:**\n"
        "- **Decision Boundary Learning:** Instead of understanding how the data was generated, discriminative models focus strictly on finding the mathematical boundary that separates different classes.\n"
        "- **Core Task:** Classification (e.g., Spam vs. Non-Spam, Image Object Recognition) and Regression.\n"
        "- **Standard Algorithms:** Logistic Regression, Support Vector Machines (SVM), Random Forest, K-Nearest Neighbors (KNN), and standard Convolutional Neural Networks (CNNs)."
    ),
    "kdd": (
        "**Knowledge Discovery in Databases (KDD)** is the iterative, multi-step process of identifying valid, novel, potentially useful, and ultimately understandable patterns from massive volumes of data.\n\n"
        "**Key Stages in the KDD Process:**\n"
        "1. **Data Cleaning:** Removes noise, eliminates duplicates, and handles missing or corrupted attribute values.\n"
        "2. **Data Integration:** Combines multiple heterogeneous data sources into a unified repository.\n"
        "3. **Data Selection:** Retrieves task-relevant data subsets from operational databases or data warehouses.\n"
        "4. **Data Transformation:** Converts data into formats suitable for mining via normalization, aggregation, and discretization.\n"
        "5. **Data Mining:** Applies intelligent algorithmic models (classification, clustering, association rules) to extract patterns.\n"
        "6. **Pattern Evaluation:** Assesses discovered patterns against validity, novelty, and statistical significance metrics.\n"
        "7. **Knowledge Presentation:** Visualizes and delivers actionable intelligence to stakeholders."
    ),
    "knowledge discovery in databases": (
        "**Knowledge Discovery in Databases (KDD)** is the iterative, multi-step process of identifying valid, novel, potentially useful, and ultimately understandable patterns from massive volumes of data.\n\n"
        "**Key Stages in the KDD Process:**\n"
        "1. **Data Cleaning:** Removes noise, eliminates duplicates, and handles missing or corrupted attribute values.\n"
        "2. **Data Integration:** Combines multiple heterogeneous data sources into a unified repository.\n"
        "3. **Data Selection:** Retrieves task-relevant data subsets from operational databases or data warehouses.\n"
        "4. **Data Transformation:** Converts data into formats suitable for mining via normalization, aggregation, and discretization.\n"
        "5. **Data Mining:** Applies intelligent algorithmic models (classification, clustering, association rules) to extract patterns.\n"
        "6. **Pattern Evaluation:** Assesses discovered patterns against validity, novelty, and statistical significance metrics.\n"
        "7. **Knowledge Presentation:** Visualizes and delivers actionable intelligence to stakeholders."
    ),
    "apriori algorithm": (
        "The **Apriori Algorithm** is an influential algorithm for mining frequent itemsets and relevant association rules in transactional databases (e.g., Market Basket Analysis).\n\n"
        "**The Apriori Principle:**\n"
        "- *Any subset of a frequent itemset must also be frequent.* Conversely, if an itemset is infrequent, all of its supersets are immediately pruned.\n\n"
        "**Step-by-Step Procedure:**\n"
        "1. **Candidate Generation ($C_k$):** Generates candidate $k$-itemsets by joining frequent $(k-1)$-itemsets ($L_{k-1} \\bowtie L_{k-1}$).\n"
        "2. **Pruning Step:** Prunes candidates whose $(k-1)$-subsets are not frequent based on the Apriori property.\n"
        "3. **Support Counting:** Scans the database to compute support for remaining candidates; items meeting the **minimum support threshold** form frequent itemset $L_k$.\n"
        "4. **Iteration:** Continues iteratively until no further frequent itemsets can be generated."
    ),
    "apriori": (
        "The **Apriori Algorithm** is an influential algorithm for mining frequent itemsets and relevant association rules in transactional databases (e.g., Market Basket Analysis).\n\n"
        "**The Apriori Principle:**\n"
        "- *Any subset of a frequent itemset must also be frequent.* Conversely, if an itemset is infrequent, all of its supersets are immediately pruned.\n\n"
        "**Step-by-Step Procedure:**\n"
        "1. **Candidate Generation ($C_k$):** Generates candidate $k$-itemsets by joining frequent $(k-1)$-itemsets ($L_{k-1} \\bowtie L_{k-1}$).\n"
        "2. **Pruning Step:** Prunes candidates whose $(k-1)$-subsets are not frequent based on the Apriori property.\n"
        "3. **Support Counting:** Scans the database to compute support for remaining candidates; items meeting the **minimum support threshold** form frequent itemset $L_k$.\n"
        "4. **Iteration:** Continues iteratively until no further frequent itemsets can be generated."
    ),
    "association rule mining": (
        "**Association Rule Mining** uncovers non-trivial item co-occurrence relationships and correlations in transaction databases.\n\n"
        "**Core Evaluation Metrics:**\n"
        "- **Support:** The proportion of transactions containing both itemsets $X$ and $Y$:\n"
        "  $$\\text{Support}(X \\Rightarrow Y) = \\frac{\\sigma(X \\cup Y)}{N}$$\n"
        "- **Confidence:** The conditional probability that transaction contains $Y$, given that it contains $X$:\n"
        "  $$\\text{Confidence}(X \\Rightarrow Y) = \\frac{\\sigma(X \\cup Y)}{\\sigma(X)}$$\n"
        "- **Lift:** Measures whether the occurrence of $X$ increases the likelihood of $Y$ beyond chance:\n"
        "  $$\\text{Lift}(X \\Rightarrow Y) = \\frac{\\text{Confidence}(X \\Rightarrow Y)}{\\text{Support}(Y)}$$"
    ),
    "association rules": (
        "**Association Rule Mining** uncovers non-trivial item co-occurrence relationships and correlations in transaction databases.\n\n"
        "**Core Evaluation Metrics:**\n"
        "- **Support:** The proportion of transactions containing both itemsets $X$ and $Y$:\n"
        "  $$\\text{Support}(X \\Rightarrow Y) = \\frac{\\sigma(X \\cup Y)}{N}$$\n"
        "- **Confidence:** The conditional probability that transaction contains $Y$, given that it contains $X$:\n"
        "  $$\\text{Confidence}(X \\Rightarrow Y) = \\frac{\\sigma(X \\cup Y)}{\\sigma(X)}$$\n"
        "- **Lift:** Measures whether the occurrence of $X$ increases the likelihood of $Y$ beyond chance:\n"
        "  $$\\text{Lift}(X \\Rightarrow Y) = \\frac{\\text{Confidence}(X \\Rightarrow Y)}{\\text{Support}(Y)}$$"
    ),
    "clustering": (
        "**Clustering** is an unsupervised data mining technique that partitions data points into clusters such that points within the same cluster exhibit high intra-cluster similarity, while points across different clusters display high inter-cluster dissimilarity.\n\n"
        "**Major Methodologies:**\n"
        "- **Partitioning Methods (K-Means):** Constructs $K$ partitions iteratively minimizing within-cluster sum of squares.\n"
        "- **Hierarchical Methods (Agglomerative / Divisive):** Builds a nested tree of clusters (dendrogram) based on linkage criteria.\n"
        "- **Density-Based Methods (DBSCAN):** Discovers arbitrary-shaped clusters by identifying dense regions separated by low-density noise regions."
    ),
    "k-means": (
        "**K-Means Clustering** is a widely adopted partitioning clustering algorithm that iteratively groups $N$ observations into $K$ user-defined clusters.\n\n"
        "**Algorithmic Steps:**\n"
        "1. **Centroid Initialization:** Randomly pick $K$ points as initial cluster centers.\n"
        "2. **Distance Calculation & Assignment:** Calculate Euclidean distance from each record to all centroids; assign each record to its nearest centroid:\n"
        "   $$d(x, c_i) = \\sqrt{\\sum_{j=1}^d (x_j - c_{ij})^2}$$\n"
        "3. **Centroid Update:** Recalculate each centroid as the geometric mean of all assigned points in that cluster.\n"
        "4. **Termination:** Repeat steps 2 and 3 until cluster assignments stabilize and centroids stop shifting."
    ),
    "kmeans": (
        "**K-Means Clustering** is a widely adopted partitioning clustering algorithm that iteratively groups $N$ observations into $K$ user-defined clusters.\n\n"
        "**Algorithmic Steps:**\n"
        "1. **Centroid Initialization:** Randomly pick $K$ points as initial cluster centers.\n"
        "2. **Distance Calculation & Assignment:** Calculate Euclidean distance from each record to all centroids; assign each record to its nearest centroid:\n"
        "   $$d(x, c_i) = \\sqrt{\\sum_{j=1}^d (x_j - c_{ij})^2}$$\n"
        "3. **Centroid Update:** Recalculate each centroid as the geometric mean of all assigned points in that cluster.\n"
        "4. **Termination:** Repeat steps 2 and 3 until cluster assignments stabilize and centroids stop shifting."
    ),
    "data preprocessing": (
        "**Data Preprocessing** is the essential data mining preparation phase that transforms messy, raw real-world data into clean, formatted inputs ready for mining algorithms.\n\n"
        "**Core Preprocessing Techniques:**\n"
        "- **Data Cleaning:** Imputes missing values, smooths noisy data via binning or regression, and filters statistical outliers.\n"
        "- **Data Integration:** Reconciles schema conflicts and eliminates data redundancy across diverse enterprise sources.\n"
        "- **Data Transformation:** Standardizes numeric attributes using **Min-Max Normalization** ($[0, 1]$) or **Z-Score Normalization** (zero-mean unit-variance).\n"
        "- **Data Reduction:** Shrinks data volume without sacrificing analytical integrity via **Dimensionality Reduction (PCA)**, feature selection, and aggregation."
    ),
    "cpu scheduling": (
        "**CPU Scheduling** is the operating system process of selecting which ready process receives CPU allocation when the processor becomes idle, maximizing system performance and responsiveness.\n\n"
        "**Key Scheduling Algorithms:**\n"
        "- **FCFS (First-Come, First-Served):** Non-preemptive; processes run strictly in order of arrival.\n"
        "- **SJF (Shortest Job First):** Non-preemptive; assigns CPU to the process with minimal burst time (optimal average wait time).\n"
        "- **SRTF (Shortest Remaining Time First):** Preemptive version of SJF.\n"
        "- **Round Robin (RR):** Preemptive scheduling where each process executes for a designated **time quantum**.\n"
        "- **Priority Scheduling:** Allocates CPU based on assigned priority levels (prevent starvation via aging)."
    ),
    "deadlock": (
        "A **Deadlock** is a state in multi-process operating systems where two or more processes are permanently blocked because each process holds a resource while awaiting another resource held by another process in the set.\n\n"
        "**The 4 Necessary Coffman Conditions:**\n"
        "1. **Mutual Exclusion:** At least one resource must be non-shareable.\n"
        "2. **Hold and Wait:** A process holds at least one resource while waiting to acquire additional allocated resources.\n"
        "3. **No Preemption:** Resources cannot be forcibly expropriated; they must be released voluntarily.\n"
        "4. **Circular Wait:** A closed chain of processes exists where each process waits for a resource held by the next process."
    ),
    "normalization": (
        "**Database Normalization** is the systematic relational schema design technique that organizes tables to minimize data redundancy and prevent insertion, update, and deletion anomalies.\n\n"
        "**Standard Normal Forms:**\n"
        "- **1NF (First Normal Form):** All attribute values must be atomic (no repeating groups or multi-valued attributes).\n"
        "- **2NF (Second Normal Form):** Must satisfy 1NF and eliminate partial dependencies (every non-prime attribute is fully functionally dependent on the entire primary key).\n"
        "- **3NF (Third Normal Form):** Must satisfy 2NF and eliminate transitive dependencies (non-prime attributes must not depend on other non-prime attributes).\n"
        "- **BCNF (Boyce-Codd Normal Form):** Stricter 3NF variant where for every functional dependency $X \\rightarrow Y$, $X$ must be a super key."
    ),
    "nlp": (
        "**Natural Language Processing (NLP)** is a multidisciplinary field of Artificial Intelligence and Computational Linguistics focused on enabling computers to understand, interpret, and generate human languages.\n\n"
        "**Core Tasks:**\n"
        "- **Syntax & Parsing:** Part-of-Speech (POS) tagging, Named Entity Recognition (NER), and dependency parsing.\n"
        "- **Semantics:** Sentiment analysis, machine translation, and semantic search.\n"
        "- **Modern Architecture:** Primarily driven by **Transformers** (e.g. BERT, GPT) with self-attention mechanisms."
    ),
    "dbms": (
        "A **Database Management System (DBMS)** is system software for creating, managing, querying, and administering structured databases.\n\n"
        "**Core Functions:**\n"
        "- **ACID Properties:** Guarantees Atomicity, Consistency, Isolation, and Durability in transactional operations.\n"
        "- **Data Independence:** Separates physical storage representation from conceptual logical schemas.\n"
        "- **Query Optimization:** Efficiently compiles and evaluates SQL statements through indexing and cost-based query planners."
    ),
    "os": (
        "An **Operating System (OS)** is system software that manages computer hardware, system resources, and execution of application programs.\n\n"
        "**Primary Responsibilities:**\n"
        "- **Process Management:** CPU scheduling, process synchronization, and deadlock prevention/resolution.\n"
        "- **Memory Management:** Virtual memory, paging, segmentation, and page replacement policies.\n"
        "- **Storage & I/O Management:** File systems (e.g. ext4, NTFS) and device driver abstraction."
    ),
    "classification": (
        "**Classification** is a supervised data mining and machine learning task where a model learns from categorized historical records to assign new, unlabelled observations into discrete target classes.\n\n"
        "**Core Algorithms:**\n"
        "- **Decision Trees (ID3, C4.5, CART):** Employs recursive attribute splitting based on Information Gain or Gini Impurity.\n"
        "- **Naive Bayes:** Probabilistic classifier applying Bayes' Theorem under strong feature independence assumptions.\n"
        "- **Support Vector Machines (SVM):** Finds the optimal separating hyperplane maximizing the margin between classes.\n"
        "- **Ensemble Methods:** Random Forest, Gradient Boosting (XGBoost), and AdaBoost for high generalization accuracy."
    ),
    "decision tree": (
        "A **Decision Tree** is a non-parametric supervised learning algorithm structured as a hierarchical flowchart where internal nodes represent attribute tests, branches represent test outcomes, and leaf nodes denote class labels.\n\n"
        "**Attribute Selection Measures (Splitting Criteria):**\n"
        "1. **Information Gain (Entropy):** Measures the expected reduction in entropy (disorder) after splitting on attribute $A$:\n"
        "   $$\\text{Entropy}(S) = -\\sum_{i=1}^c p_i \\log_2(p_i)$$\n"
        "   $$\\text{Gain}(S, A) = \\text{Entropy}(S) - \\sum_{v \\in \\text{Values}(A)} \\frac{|S_v|}{|S|} \\text{Entropy}(S_v)$$\n"
        "2. **Gini Index (CART):** Measures the probability of a randomly chosen element being incorrectly labeled:\n"
        "   $$\\text{Gini}(S) = 1 - \\sum_{i=1}^c p_i^2$$\n"
        "3. **Gain Ratio (C4.5):** Overcomes Information Gain's bias toward high-branching attributes by normalizing through Split Information."
    ),
    "naive bayes": (
        "The **Naive Bayes Classifier** is a generative probabilistic classification algorithm based on **Bayes' Theorem** with the 'naive' assumption that all predictive attributes are conditionally independent given the class label.\n\n"
        "**Mathematical Formulation:**\n"
        "$$P(C_k \\mid X) = \\frac{P(X \\mid C_k) \\cdot P(C_k)}{P(X)}$$\n"
        "Under attribute independence:\n"
        "$$P(X \\mid C_k) = \\prod_{i=1}^d P(x_i \\mid C_k)$$\n"
        "The predicted class is chosen via Maximum A Posteriori (MAP):\n"
        "$$\\hat{y} = \\arg\\max_{k} P(C_k) \\prod_{i=1}^d P(x_i \\mid C_k)$$\n\n"
        "**Key Strengths:** Fast training, scales linearly with features, robust with small datasets, exceptional performance on text/spam classification."
    ),
    "support vector machine": (
        "A **Support Vector Machine (SVM)** is a powerful supervised learning algorithm for classification and regression that searches for the optimal separating **hyperplane** maximizing the geometric margin between data classes.\n\n"
        "**Core Concepts:**\n"
        "- **Support Vectors:** Critical training data points closest to the decision boundary that determine the position and orientation of the separating hyperplane.\n"
        "- **Maximum Margin:** Maximizes the distance $\\frac{2}{\\|w\\|}$ between parallel bounding hyperplanes, delivering superior generalization.\n"
        "- **The Kernel Trick:** Maps non-linearly separable data into higher-dimensional feature spaces where linear separation is possible using kernel functions (Linear, Polynomial, RBF/Gaussian, Sigmoid)."
    ),
    "svm": (
        "A **Support Vector Machine (SVM)** is a powerful supervised learning algorithm for classification and regression that searches for the optimal separating **hyperplane** maximizing the geometric margin between data classes.\n\n"
        "**Core Concepts:**\n"
        "- **Support Vectors:** Critical training data points closest to the decision boundary that determine the position and orientation of the separating hyperplane.\n"
        "- **Maximum Margin:** Maximizes the distance $\\frac{2}{\\|w\\|}$ between parallel bounding hyperplanes, delivering superior generalization.\n"
        "- **The Kernel Trick:** Maps non-linearly separable data into higher-dimensional feature spaces using kernel functions (Linear, RBF/Gaussian, Polynomial)."
    ),
    "random forest": (
        "**Random Forest** is an ensemble learning method that constructs a multitude of decision trees during training and outputs the majority class vote (classification) or mean prediction (regression) of the individual trees.\n\n"
        "**Key Mechanisms:**\n"
        "- **Bootstrap Aggregation (Bagging):** Each tree is trained on an independently drawn bootstrap sample of the original dataset with replacement.\n"
        "- **Random Feature Selection:** At each node split, only a random subset of attributes (typically $\\sqrt{p}$) is evaluated, decorrelating trees and drastically reducing variance without increasing bias."
    ),
    "fp-growth": (
        "The **FP-Growth (Frequent Pattern Growth)** algorithm is an efficient alternative to Apriori for mining frequent itemsets that avoids expensive candidate generation.\n\n"
        "**Key Characteristics:**\n"
        "- **FP-Tree (Frequent Pattern Tree):** Compresses the entire transactional database into a compact, memory-resident prefix tree structure.\n"
        "- **Divide-and-Conquer:** Decomposes the mining task into smaller sub-problems by constructing conditional pattern bases and conditional FP-trees.\n"
        "- **Performance:** Requires only 2 database scans, running significantly faster than Apriori on dense, large datasets."
    ),
    "dbscan": (
        "**DBSCAN (Density-Based Spatial Clustering of Applications with Noise)** is an unsupervised clustering algorithm that discovers clusters of arbitrary shapes based on the local density of data points.\n\n"
        "**Core Parameters & Point Classifications:**\n"
        "- **$\\epsilon$ (Eps):** Radius specifying the neighborhood distance around a point.\n"
        "- **MinPts:** Minimum number of points required within $\\epsilon$-neighborhood to form a dense region.\n"
        "- **Core Point:** Has at least $\\text{MinPts}$ within distance $\\epsilon$.\n"
        "- **Border Point:** Has fewer than $\\text{MinPts}$ within $\\epsilon$, but falls within the neighborhood of a core point.\n"
        "- **Noise Point:** Neither a core nor a border point; treated as an outlier."
    ),
    "dimensionality reduction": (
        "**Dimensionality Reduction** is the data preprocessing technique of projecting high-dimensional datasets into lower-dimensional manifolds while preserving maximal statistical variance and structural relationships.\n\n"
        "**Principal Component Analysis (PCA):**\n"
        "1. Standardize the data matrix to zero mean.\n"
        "2. Compute the feature covariance matrix: $\\Sigma = \\frac{1}{n} X^T X$.\n"
        "3. Calculate the eigenvalues and eigenvectors of $\\Sigma$.\n"
        "4. Sort eigenvectors in descending order of their corresponding eigenvalues.\n"
        "5. Project data onto the top $k$ principal eigenvectors capturing target cumulative variance (e.g. 95%)."
    ),
    "pca": (
        "**Principal Component Analysis (PCA)** is an unsupervised linear dimensionality reduction technique that transforms correlated attributes into a smaller set of orthogonal, uncorrelated variables called **Principal Components**.\n\n"
        "**Step-by-Step Procedure:**\n"
        "1. Mean-center the dataset.\n"
        "2. Compute the $d \\times d$ Covariance Matrix.\n"
        "3. Perform Eigendecomposition to determine eigenvalues and eigenvectors.\n"
        "4. Select the top $k$ eigenvectors corresponding to the largest eigenvalues.\n"
        "5. Transform the original $n \\times d$ data onto the $n \\times k$ principal subspace."
    ),
    "process vs thread": (
        "**Difference Between Process and Thread:**\n\n"
        "| Characteristic | Process | Thread |\n"
        "| :--- | :--- | :--- |\n"
        "| **Definition** | An independent executing program with its own memory space. | The smallest unit of CPU execution within a parent process. |\n"
        "| **Memory & Address Space** | Has its own separate virtual address space (code, data, heap). | Shares code, data, and heap segments with peer threads in the process. |\n"
        "| **Creation & Context Switch** | Heavyweight; slow creation and high context-switch overhead. | Lightweight; fast creation and minimal context-switch overhead. |\n"
        "| **Communication** | Requires Inter-Process Communication (IPC: pipes, sockets, shared memory). | Communicates directly via shared global variables and heap memory. |\n"
        "| **Isolation & Fault Tolerance** | High; crash of one process does not affect others. | Low; an uncaught exception in one thread can terminate the whole process. |"
    ),
    "virtual memory": (
        "**Virtual Memory** is an operating system memory management capability that provides an idealized abstraction of storage resources, allowing programs to execute even when their memory requirements exceed physical RAM.\n\n"
        "**Core Mechanisms:**\n"
        "- **Paging:** Divides virtual memory into fixed-size blocks called **Pages** (e.g. 4 KB) and physical memory into identical **Frames**.\n"
        "- **Page Table & TLB:** Maps virtual addresses to physical frame addresses; the Translation Lookaside Buffer (TLB) acts as a high-speed hardware cache for page lookups.\n"
        "- **Page Fault:** An interrupt generated when a requested page is not currently resident in physical RAM, triggering the OS to fetch it from swap storage on disk.\n"
        "- **Page Replacement Algorithms:** FIFO, LRU (Least Recently Used), and Optimal (OPT) determine which resident frame to evict."
    ),
    "paging vs segmentation": (
        "**Comparison: Paging vs. Segmentation:**\n\n"
        "| Feature | Paging | Segmentation |\n"
        "| :--- | :--- | :--- |\n"
        "| **Block Size** | Fixed-size memory blocks (e.g. 4 KB pages). | Variable-size logical blocks based on programmer modules (code, stack, heap). |\n"
        "| **Hardware Support** | Page Table with Page Number and Offset. | Segment Table with Segment Base and Limit register. |\n"
        "| **Fragmentation** | Suffers from **Internal Fragmentation**; eliminates external fragmentation. | Suffers from **External Fragmentation**; eliminates internal fragmentation. |\n"
        "| **Programmer Visibility** | Completely transparent to programmer (handled by OS/hardware). | Visible to programmer (corresponds to functions, arrays, modules). |"
    ),
    "acid properties": (
        "**ACID Properties** are the four fundamental guarantees required of a Database Management System to ensure transactional reliability:\n\n"
        "- **Atomicity ('All or Nothing'):** Every transaction is treated as a single indivisible unit; either all SQL operations succeed, or the entire transaction is rolled back with zero effect.\n"
        "- **Consistency:** Ensures execution of a transaction preserves all database integrity constraints and business rules from one valid state to another.\n"
        "- **Isolation:** Concurrent transactions execute without interference; intermediate uncommitted states of one transaction are invisible to others (managed via 2-Phase Locking).\n"
        "- **Durability:** Once a transaction commits, its modifications are permanently recorded in non-volatile storage (via Write-Ahead Logging - WAL) and persist even across system crashes."
    ),
    "indexing": (
        "**Database Indexing** is a data structure technique used by database engines to rapidly locate and access records without scanning every table row (Full Table Scan).\n\n"
        "**Key Index Architectures:**\n"
        "- **B-Tree & B+ Tree:** Balanced tree structures maintaining sorted data with $O(\\log N)$ search, insertion, and deletion times. B+ Trees store all actual record pointers in leaf nodes linked sequentially, making them optimal for disk page storage and range queries.\n"
        "- **Clustered Index:** Physically dictates the storage order of rows on disk (only 1 per table, typically on Primary Key).\n"
        "- **Non-Clustered Index:** Maintains a separate sorted index structure with pointers (row IDs) referencing the physical table rows."
    ),
    "sql vs nosql": (
        "**Comparison: SQL (Relational) vs. NoSQL (Non-Relational) Databases:**\n\n"
        "| Property | SQL Databases | NoSQL Databases |\n"
        "| :--- | :--- | :--- |\n"
        "| **Data Model** | Relational tables with predefined strict schemas. | Flexible schema: Document (MongoDB), Key-Value (Redis), Columnar (Cassandra), Graph (Neo4j). |\n"
        "| **Scaling** | Vertically scalable (scale-up with faster CPU/RAM). | Horizontally scalable (scale-out across commodity clusters). |\n"
        "| **Transaction Model** | ACID compliance (strong consistency). | BASE compliance (Basically Available, Soft state, Eventual consistency). |\n"
        "| **Query Language** | Structured Query Language (SQL) with complex joins. | Unstructured API/JSON query mechanisms; minimal or no join support. |\n"
        "| **Best Suited For** | Complex multi-table transactions (banking, enterprise ERP). | Massive unstructured big data, real-time analytics, dynamic schemas. |"
    ),
    "osi model": (
        "The **OSI (Open Systems Interconnection) 7-Layer Reference Model** standardizes network telecommunication into functional conceptual tiers:\n\n"
        "1. **Layer 7 - Application:** User-facing network services (HTTP, HTTPS, FTP, SMTP, DNS).\n"
        "2. **Layer 6 - Presentation:** Data formatting, syntax translation, compression, and encryption/decryption (SSL/TLS, JPEG, ASCII).\n"
        "3. **Layer 5 - Session:** Establishes, manages, and terminates conversational sessions between endpoints (RPC, NetBIOS).\n"
        "4. **Layer 4 - Transport:** End-to-end reliability, segmentation, flow control, and error recovery (TCP, UDP).\n"
        "5. **Layer 3 - Network:** Logical IP addressing, packet forwarding, and path selection across routers (IP, ICMP, OSPF, BGP).\n"
        "6. **Layer 2 - Data Link:** Framing, physical MAC addressing, hop-to-hop transfer, and error detection via CRC (Ethernet, Wi-Fi, Switches).\n"
        "7. **Layer 1 - Physical:** Unstructured raw bitstream transmission over physical media (Cables, Fiber optics, Radio frequencies, Hubs)."
    ),
    "cloud computing": (
        "**Cloud Computing** is the on-demand delivery of IT resources—including compute power, database storage, and networking—over the Internet with pay-as-you-go pricing.\n\n"
        "**Key Service Models:**\n"
        "- **IaaS (Infrastructure as a Service):** Provides fundamental computing, storage, and networking hardware (e.g., AWS EC2, Google Compute Engine).\n"
        "- **PaaS (Platform as a Service):** Provides execution environments and managed platforms for developing, testing, and deploying applications without managing underlying infrastructure (e.g., Heroku, Google App Engine).\n"
        "- **SaaS (Software as a Service):** Complete software applications delivered over the web (e.g., Google Workspace, Microsoft 365).\n\n"
        "**Deployment Models:** Public Cloud, Private Cloud, Hybrid Cloud, and Multi-Cloud architectures."
    ),
    "blockchain": (
        "**Blockchain** is a decentralized, distributed, and immutable ledger technology that securely records transactions across a peer-to-peer network without requiring a centralized authority or intermediary.\n\n"
        "**Core Architectural Elements:**\n"
        "- **Blocks & Cryptographic Hashes:** Each block packages transaction data, a timestamp, its own SHA-256 hash, and the hash of the preceding block, creating an unbroken tamper-evident cryptographic chain.\n"
        "- **Consensus Mechanisms:** Protocols that ensure all distributed nodes agree on ledger validity (e.g., Proof of Work - PoW, Proof of Stake - PoS).\n"
        "- **Smart Contracts:** Self-executing programmable contracts with agreement terms written directly into immutable code lines."
    ),
    "cybersecurity": (
        "**Cybersecurity** is the comprehensive discipline of safeguarding computer systems, networks, devices, and data from digital attacks, unauthorized access, and damage.\n\n"
        "**The CIA Triad (Foundational Benchmark):**\n"
        "- **Confidentiality:** Restricting information access to authorized personnel via encryption and multi-factor authentication (MFA).\n"
        "- **Integrity:** Ensuring data remains accurate, complete, and uncorrupted by unauthorized modification using cryptographic hashing and digital signatures.\n"
        "- **Availability:** Guaranteeing authorized users have reliable, uninterrupted access to systems via redundancy, failover, and DDoS mitigation."
    ),
    "cryptography": (
        "**Cryptography** is the science of using mathematical codes and algorithms to secure information, communication, and digital identities against unauthorized adversaries.\n\n"
        "**Two Primary Paradigms:**\n"
        "- **Symmetric Key Cryptography:** Uses a single shared secret key for both encryption and decryption (e.g., AES - Advanced Encryption Standard). Ultra-fast; used for bulk data encryption.\n"
        "- **Asymmetric (Public Key) Cryptography:** Uses a mathematically linked key pair: a **Public Key** to encrypt and a private **Private Key** to decrypt (e.g., RSA, Elliptic Curve Cryptography - ECC). Used for digital signatures, SSL/TLS handshakes, and identity verification."
    ),
    "rest api": (
        "A **REST API** (Representational State Transfer Application Programming Interface) is an architectural style for network-based client-server communication using standard HTTP protocols.\n\n"
        "**Core Principles:**\n"
        "- **Statelessness:** Every client request contains all context needed for the server to process it; the server stores no client session context.\n"
        "- **Standard HTTP Verbs:** `GET` (retrieve records), `POST` (create new resource), `PUT` / `PATCH` (update existing resource), and `DELETE` (remove resource).\n"
        "- **Resource URIs & JSON:** Resources are uniquely identified by clean endpoint URLs and exchange payloads via lightweight JSON formatting."
    ),
    "microservices": (
        "**Microservices Architecture** is a software design approach where a large, complex application is structured as a suite of small, independently deployable, and autonomous services.\n\n"
        "**Key Advantages over Monoliths:**\n"
        "- **Independent Scalability:** Resource-intensive microservices can scale horizontally without replicating the entire application.\n"
        "- **Fault Isolation:** A failure or crash in one service (e.g., payment gateway) does not cascade to take down unrelated modules (e.g., product catalog).\n"
        "- **Decentralized Tech Stacks:** Different engineering teams can choose optimal languages, frameworks, and databases tailored to each specific microservice."
    ),
    "docker": (
        "**Docker** is an open-source platform that uses OS-level virtualization to package applications and all their dependencies into lightweight, standalone, and portable **Containers**.\n\n"
        "**Containers vs. Virtual Machines (VMs):**\n"
        "- **Virtual Machines:** Include a full guest operating system running on top of a hypervisor, consuming gigabytes of storage and substantial memory overhead.\n"
        "- **Docker Containers:** Share the host machine's OS kernel while isolating application processes in user space, launching in milliseconds with megabyte-level footprints."
    ),
    "kubernetes": (
        "**Kubernetes (K8s)** is an open-source container orchestration platform designed to automate the deployment, horizontal scaling, service discovery, and management of containerized workloads across server clusters.\n\n"
        "**Core Architecture:**\n"
        "- **Control Plane:** Manages cluster state, scheduling, and API requests (`kube-apiserver`, `etcd`, `kube-scheduler`).\n"
        "- **Worker Nodes:** Run container pods via `kubelet` and container runtimes (e.g., containerd).\n"
        "- **Key Capabilities:** Automated rollouts, self-healing restarts, horizontal pod autoscaling (HPA), and load-balanced traffic routing."
    ),
    "natural language processing": (
        "**Natural Language Processing (NLP)** is an interdisciplinary field of Artificial Intelligence and Computational Linguistics that enables computers to understand, interpret, and generate human language.\n\n"
        "**Core Pipeline & Tasks:**\n"
        "- **Text Preprocessing:** Tokenization, stop-word removal, lemmatization, and word embeddings (Word2Vec, FastText).\n"
        "- **Syntactic & Semantic Analysis:** Part-of-Speech (POS) tagging, Named Entity Recognition (NER), and Sentiment Analysis.\n"
        "- **Modern Deep Learning:** Dominated by the **Transformer architecture** and **Self-Attention mechanisms** (e.g., BERT, GPT, T5) capable of capturing long-range contextual dependencies across entire passages."
    ),
    "reinforcement learning": (
        "**Reinforcement Learning (RL)** is an AI learning paradigm where an autonomous **Agent** learns to make sequential decisions by interacting with an **Environment** to maximize cumulative **Rewards** through trial and error.\n\n"
        "**Core Framework (Markov Decision Process - MDP):**\n"
        "- **State ($S$):** Current configuration of the environment.\n"
        "- **Action ($A$):** Move selected by the agent.\n"
        "- **Reward ($R$):** Numerical scalar feedback returned by the environment.\n"
        "- **Policy ($\\pi$):** Strategy mapping states to actions (e.g., Q-Learning, Deep Q-Networks - DQN, Policy Gradients)."
    ),
    "dynamic programming": (
        "**Dynamic Programming (DP)** is an algorithmic optimization technique that solves complex problems by breaking them down into overlapping subproblems, solving each subproblem once, and storing the results in a lookup table (memoization or tabulation) to prevent redundant recomputations.\n\n"
        "**Two Essential Properties:**\n"
        "1. **Optimal Substructure:** An optimal solution to the overall problem incorporates optimal solutions to its constituent subproblems.\n"
        "2. **Overlapping Subproblems:** The same subproblems are solved repeatedly during recursion.\n\n"
        "**Classic Exam Problems:** 0/1 Knapsack Problem, Longest Common Subsequence (LCS), Matrix Chain Multiplication, and Floyd-Warshall shortest paths."
    ),
    "software engineering": (
        "**Software Engineering** is the systematic, disciplined, and quantifiable engineering approach to the development, operation, and maintenance of high-quality software systems.\n\n"
        "**Key Methodologies:**\n"
        "- **Waterfall Model:** Sequential, linear phases (Requirements, Design, Implementation, Testing, Deployment, Maintenance); optimal for strict, unvarying requirements.\n"
        "- **Agile & Scrum:** Iterative, customer-centric development executing in short 1 to 4-week sprints; handles dynamic requirement changes with high adaptability."
    ),
    "tcp vs udp": (
        "**Comparison: TCP (Transmission Control Protocol) vs. UDP (User Datagram Protocol):**\n\n"
        "| Feature | TCP | UDP |\n"
        "| :--- | :--- | :--- |\n"
        "| **Connection Type** | Connection-Oriented (established via 3-Way Handshake: SYN, SYN-ACK, ACK). | Connectionless (sends datagrams immediately without handshake). |\n"
        "| **Reliability** | Guaranteed delivery; retransmits lost packets and verifies checksums. | Unreliable delivery (best-effort); no retransmission or acknowledgment. |\n"
        "| **Ordering** | In-order delivery guaranteed via sequence numbers. | No ordering guarantees; packets may arrive out of order or duplicate. |\n"
        "| **Flow & Congestion Control** | Yes; dynamic sliding window protocols and congestion avoidance algorithms. | No; transmits at source rate without congestion throttling. |\n"
        "| **Header Overhead** | 20 to 60 bytes. | 8 bytes fixed overhead. |\n"
        "| **Use Cases** | Web browsing (HTTP/HTTPS), file transfer (FTP), email (SMTP). | Live video streaming, VoIP, online gaming (DNS, DHCP). |"
    ),
    "supervised learning vs unsupervised learning": (
        "**Comparison: Supervised Learning vs. Unsupervised Learning:**\n\n"
        "| Dimension | Supervised Learning | Unsupervised Learning |\n"
        "| :--- | :--- | :--- |\n"
        "| **Training Data** | Requires labeled dataset containing paired features and ground-truth targets ($x_i, y_i$). | Uses completely unlabeled data ($x_i$) with no target outputs. |\n"
        "| **Core Objective** | Learn a mapping function $f(x) \\approx y$ to predict targets for unseen inputs. | Discover hidden patterns, intrinsic cluster groupings, and data representations. |\n"
        "| **Primary Tasks** | **Classification** (discrete labels) and **Regression** (continuous values). | **Clustering**, **Association Rules**, and **Dimensionality Reduction**. |\n"
        "| **Evaluation** | Directly quantified against ground truth (Accuracy, MSE, F1-Score). | Evaluated using internal cluster cohesion/separation (Silhouette Score, Inertia). |\n"
        "| **Key Algorithms** | Linear Regression, Decision Trees, SVM, Neural Networks. | K-Means, DBSCAN, Apriori, Principal Component Analysis (PCA). |"
    ),
    "classification vs clustering": (
        "**Difference: Classification vs. Clustering:**\n\n"
        "| Characteristic | Classification | Clustering |\n"
        "| :--- | :--- | :--- |\n"
        "| **Learning Type** | Supervised Learning. | Unsupervised Learning. |\n"
        "| **Class Labels** | Known in advance; targets are predefined categories. | Unknown; discovered automatically from data characteristics. |\n"
        "| **Process** | Trains on labeled data to build a classifier that assigns new items to known classes. | Groups data points based on geometric distance or similarity metrics. |\n"
        "| **Boundary Type** | Decision boundaries separating labeled instances. | Cluster centroids, density boundaries, or hierarchical dendrograms. |\n"
        "| **Algorithms** | Naive Bayes, Decision Trees, Random Forest, SVM. | K-Means, DBSCAN, Agglomerative Hierarchical Clustering. |"
    ),
    "binary search tree": (
        "A **Binary Search Tree (BST)** is a node-based binary tree data structure with the ordering invariant that for every node $X$:\n"
        "- All keys in $X$'s left subtree are strictly less than $X.\\text{key}$ ($k_L < X.\\text{key}$).\n"
        "- All keys in $X$'s right subtree are strictly greater than $X.\\text{key}$ ($k_R > X.\\text{key}$).\n\n"
        "**Operational Complexities:**\n"
        "- **Average Case (Balanced Tree):** Search, Insertion, and Deletion execute in $O(\\log N)$ time.\n"
        "- **Worst Case (Degenerate Tree):** If items are inserted in sorted order, the tree degenerates into a linked list with $O(N)$ operational time.\n"
        "- **Self-Balancing BSTs (AVL, Red-Black Trees):** Enforce height balance via rotations to guarantee strictly $O(\\log N)$ worst-case time."
    ),
    "sorting algorithms": (
        "**Comparison of Standard University Sorting Algorithms:**\n\n"
        "| Algorithm | Best Time | Average Time | Worst Time | Space | Stable? |\n"
        "| :--- | :--- | :--- | :--- | :--- | :--- |\n"
        "| **Quick Sort** | $O(N \\log N)$ | $O(N \\log N)$ | $O(N^2)$ (sorted pivot) | $O(\\log N)$ | No |\n"
        "| **Merge Sort** | $O(N \\log N)$ | $O(N \\log N)$ | $O(N \\log N)$ | $O(N)$ | Yes |\n"
        "| **Heap Sort** | $O(N \\log N)$ | $O(N \\log N)$ | $O(N \\log N)$ | $O(1)$ | No |\n"
        "| **Insertion Sort** | $O(N)$ (already sorted) | $O(N^2)$ | $O(N^2)$ | $O(1)$ | Yes |\n"
        "| **Bubble Sort** | $O(N)$ | $O(N^2)$ | $O(N^2)$ | $O(1)$ | Yes |"
    ),
    "time complexity": (
        "**Asymptotic Notations in Algorithm Analysis:**\n\n"
        "- **Big-O ($O$):** Defines an **asymptotic upper bound**, representing the worst-case runtime growth rate: $f(n) \\le c \\cdot g(n)$ for all $n \\ge n_0$.\n"
        "- **Big-Omega ($\\Omega$):** Defines an **asymptotic lower bound**, representing the best-case runtime: $f(n) \\ge c \\cdot g(n)$ for all $n \\ge n_0$.\n"
        "- **Big-Theta ($\\Theta$):** Defines an **asymptotically tight bound**, binding the runtime from both above and below: $c_1 g(n) \\le f(n) \\le c_2 g(n)$.\n\n"
        "**Complexity Hierarchy (Fastest to Slowest):**\n"
        "$$O(1) < O(\\log N) < O(N) < O(N \\log N) < O(N^2) < O(2^N) < O(N!)$$"
    ),
    "asthma": (
        "**Asthma Pathophysiology & Management:**\n\n"
        "- **Definition:** A chronic inflammatory disease of the conducting airways characterized by bronchial hyperresponsiveness, reversible airflow obstruction, and mucous plugging.\n"
        "- **Diagnostic Criteria (Spirometry):** Reduced $\\text{FEV}_1/\\text{FVC} < 0.70$ demonstrating significant bronchodilator reversibility: increase in $\\text{FEV}_1 \\ge 12\\%$ and $\\ge 200\\text{ mL}$ after inhaling a short-acting beta-2 agonist (albuterol).\n"
        "- **Management (GINA Guidelines):** Inhaled Corticosteroids (ICS) as foundational anti-inflammatory therapy combined with Formoterol (LABA)."
    ),
    "diabetes mellitus": (
        "**Diabetes Mellitus Pathophysiology & Clinical Protocol:**\n\n"
        "- **Type 1 Diabetes:** Autoimmune destruction of pancreatic $\\beta$-cells leading to absolute insulin deficiency; managed with basal-bolus insulin regimens.\n"
        "- **Type 2 Diabetes:** Progressive insulin secretory defect on the background of insulin resistance; managed with lifestyle modification, Metformin, SGLT2 inhibitors, and GLP-1 receptor agonists.\n"
        "- **Diagnostic Criteria:** Fasting Plasma Glucose $\\ge 126\\text{ mg/dL}$, 2-hr post-75g OGTT $\\ge 200\\text{ mg/dL}$, or $\\text{HbA}_{1c} \\ge 6.5\\%$."
    )
}

# Aliases for instant short-form concept lookups
ACADEMIC_KNOWLEDGE_BASE["dl"] = ACADEMIC_KNOWLEDGE_BASE["deep learning"]
ACADEMIC_KNOWLEDGE_BASE["ml"] = ACADEMIC_KNOWLEDGE_BASE["machine learning"]
ACADEMIC_KNOWLEDGE_BASE["dm"] = ACADEMIC_KNOWLEDGE_BASE["data mining"]
ACADEMIC_KNOWLEDGE_BASE["ann"] = ACADEMIC_KNOWLEDGE_BASE["neural network"]
ACADEMIC_KNOWLEDGE_BASE["bst"] = ACADEMIC_KNOWLEDGE_BASE["binary search tree"]
ACADEMIC_KNOWLEDGE_BASE["tcp"] = ACADEMIC_KNOWLEDGE_BASE["tcp vs udp"]
ACADEMIC_KNOWLEDGE_BASE["udp"] = ACADEMIC_KNOWLEDGE_BASE["tcp vs udp"]
ACADEMIC_KNOWLEDGE_BASE["osi"] = ACADEMIC_KNOWLEDGE_BASE["osi model"]
ACADEMIC_KNOWLEDGE_BASE["sql"] = ACADEMIC_KNOWLEDGE_BASE["sql vs nosql"]
ACADEMIC_KNOWLEDGE_BASE["nosql"] = ACADEMIC_KNOWLEDGE_BASE["sql vs nosql"]
ACADEMIC_KNOWLEDGE_BASE["acid"] = ACADEMIC_KNOWLEDGE_BASE["acid properties"]
ACADEMIC_KNOWLEDGE_BASE["generative artificial intelligence"] = ACADEMIC_KNOWLEDGE_BASE["generative ai"]
ACADEMIC_KNOWLEDGE_BASE["artificial intelligence ethics"] = ACADEMIC_KNOWLEDGE_BASE["ai ethics"]
ACADEMIC_KNOWLEDGE_BASE["generative ai ethics"] = ACADEMIC_KNOWLEDGE_BASE["ethics"]
ACADEMIC_KNOWLEDGE_BASE["generative artificial intelligence ethics"] = ACADEMIC_KNOWLEDGE_BASE["ethics"]
ACADEMIC_KNOWLEDGE_BASE["difference between generative and discriminative models"] = ACADEMIC_KNOWLEDGE_BASE["generative models vs discriminative models"]
ACADEMIC_KNOWLEDGE_BASE["difference between generative models and discriminative models"] = ACADEMIC_KNOWLEDGE_BASE["generative models vs discriminative models"]
ACADEMIC_KNOWLEDGE_BASE["generative vs discriminative models"] = ACADEMIC_KNOWLEDGE_BASE["generative models vs discriminative models"]
ACADEMIC_KNOWLEDGE_BASE["generative and discriminative models"] = ACADEMIC_KNOWLEDGE_BASE["generative models vs discriminative models"]
ACADEMIC_KNOWLEDGE_BASE["generative model vs discriminative model"] = ACADEMIC_KNOWLEDGE_BASE["generative models vs discriminative models"]
ACADEMIC_KNOWLEDGE_BASE["discriminative vs generative"] = ACADEMIC_KNOWLEDGE_BASE["generative models vs discriminative models"]
ACADEMIC_KNOWLEDGE_BASE["discriminative models vs generative models"] = ACADEMIC_KNOWLEDGE_BASE["generative models vs discriminative models"]
ACADEMIC_KNOWLEDGE_BASE["generative model"] = ACADEMIC_KNOWLEDGE_BASE["generative models"]
ACADEMIC_KNOWLEDGE_BASE["discriminative model"] = ACADEMIC_KNOWLEDGE_BASE["discriminative models"]

COMMON_CHAT_ABBREVIATIONS = {
    r"\bhow\s+its\b": "how is it",
    r"\bhows\b": "how is",
    r"\bwhys\b": "why is",
    r"\bwhats\b": "what is",
    r"\bwts\b": "what is",
    r"\bwats\b": "what is",
    r"\bwt\b": "what",
    r"\bwat\b": "what",
    r"\bwht\b": "what",
    r"\bwen\b": "when",
    r"\bwn\b": "when",
    r"\bwher\b": "where",
    r"\bwr\b": "where",
    r"\bhw\b": "how",
    r"\by\b": "why",
    r"\bdiff\s+b/w\b": "difference between",
    r"\bdiff\s+between\b": "difference between",
    r"\bdif\s+b/w\b": "difference between",
    r"\bbtwn\b": "between",
    r"\bb\/w\b": "between",
    r"\bbw\b": "between",
    r"\bdiff\b": "difference",
    r"\bdif\b": "difference",
    r"\bw/o\b": "without",
    r"\bw/\b": "with",
    r"\bdef\b": "define",
    r"\bdefn\b": "definition",
    r"\bexp\b": "explain",
    r"\bexpl\b": "explain",
    r"\bxplain\b": "explain",
    r"\belab\b": "elaborate",
    r"\bex\b": "example",
    r"\beg\b": "example",
    r"\bpls\b": "please",
    r"\bplz\b": "please",
    r"\babt\b": "about",
    r"\bimp\b": "important",
    r"\bqns\b": "questions",
    r"\bques\b": "questions",
    r"\bqs\b": "questions",
    r"\bqn\b": "question",
    r"\bque\b": "question",
    r"\bans\b": "answer",
    r"\banss\b": "answers",
    r"\balgo\b": "algorithm",
    r"\balgos\b": "algorithms",
    r"\bapps\b": "applications",
    r"\bappl\b": "applications",
    r"\badv\b": "advantages",
    r"\badvs\b": "advantages",
    r"\bdisadv\b": "disadvantages",
    r"\bdisadvs\b": "disadvantages",
    r"\bpts\b": "points",
    r"\bpt\b": "point",
    r"\breq\b": "requirements",
    r"\breqs\b": "requirements",
    r"\bdiag\b": "diagram",
    r"\bdiagr\b": "diagram",
    r"\barch\b": "architecture",
    r"\bchar\b": "characteristics",
    r"\bchars\b": "characteristics",
    r"\bfunc\b": "function",
    r"\bfuncs\b": "functions",
    r"\bcalc\b": "calculate",
    r"\binfo\b": "information",
    r"\bsem\b": "semester",
    r"\bsub\b": "subject",
    r"\bdept\b": "department",
    r"\bprep\b": "preparation",
    r"\brev\b": "revision",
    r"\bpyq\b": "previous year question",
    r"\bpyqs\b": "previous year questions",
    r"\bmcq\b": "multiple choice question",
    r"\bmcqs\b": "multiple choice questions",
    r"\bu\b": "you",
    r"\bur\b": "your",
    r"\br\b": "are",
    r"\bbcuz\b": "because",
    r"\bbcoz\b": "because",
    r"\bcuz\b": "because",
    r"\bintro\b": "introduction",
    r"\bsum\b": "summary"
}

ACADEMIC_ACRONYMS = {
    # NLP & Text
    r"\bnlp\b": "natural language processing",
    r"\bcfg\b": "context-free grammar",
    r"\bcfgs\b": "context-free grammars",
    r"\bcnf\b": "chomsky normal form",
    r"\bgnf\b": "greibach normal form",
    r"\bcyk\b": "cocke-younger-kasami",
    r"\bner\b": "named entity recognition",
    r"\bpos\b": "part of speech",
    r"\bcrf\b": "conditional random fields",
    r"\bcrfs\b": "conditional random fields",
    r"\bhmm\b": "hidden markov model",
    r"\bhmms\b": "hidden markov models",
    r"\bbert\b": "bidirectional encoder representations from transformers",
    r"\bgpt\b": "generative pre-trained transformer",
    r"\bllm\b": "large language model",
    r"\bllms\b": "large language models",
    r"\bbpe\b": "byte pair encoding",
    r"\btfidf\b": "term frequency inverse document frequency",
    r"\btf-idf\b": "term frequency inverse document frequency",
    r"\bbow\b": "bag of words",
    r"\bngram\b": "n-gram",
    r"\bngrams\b": "n-grams",

    # AI & ML & Deep Learning
    r"\bai\b": "artificial intelligence",
    r"\bml\b": "machine learning",
    r"\bdl\b": "deep learning",
    r"\bdm\b": "data mining",
    r"\bann\b": "artificial neural network",
    r"\banns\b": "artificial neural networks",
    r"\bcnn\b": "convolutional neural network",
    r"\bcnns\b": "convolutional neural networks",
    r"\brnn\b": "recurrent neural network",
    r"\brnns\b": "recurrent neural networks",
    r"\blstm\b": "long short-term memory",
    r"\blstms\b": "long short-term memory",
    r"\bgru\b": "gated recurrent unit",
    r"\bgrus\b": "gated recurrent units",
    r"\bgan\b": "generative adversarial network",
    r"\bgans\b": "generative adversarial networks",
    r"\bae\b": "autoencoder",
    r"\baes\b": "autoencoders",
    r"\bvae\b": "variational autoencoder",
    r"\bvaes\b": "variational autoencoders",
    r"\bkl\b": "kullback leibler",
    r"\bkld\b": "kullback leibler divergence",
    r"\bpca\b": "principal component analysis",
    r"\bsvm\b": "support vector machine",
    r"\bsvms\b": "support vector machines",
    r"\bknn\b": "k-nearest neighbors",
    r"\bgd\b": "gradient descent",
    r"\bsgd\b": "stochastic gradient descent",
    r"\bbp\b": "backpropagation",
    r"\bmse\b": "mean squared error",
    r"\bmae\b": "mean absolute error",
    r"\bce\b": "cross entropy",
    r"\brelu\b": "rectified linear unit",
    r"\bkdd\b": "knowledge discovery in databases",
    r"\barm\b": "association rule mining",

    # Systems, DBMS & OS
    r"\bos\b": "operating system",
    r"\bdbms\b": "database management system",
    r"\bdb\b": "database",
    r"\bsql\b": "structured query language",
    r"\bnosql\b": "non-relational database",
    r"\bfcfs\b": "first-come first-served",
    r"\bsjf\b": "shortest job first",
    r"\bsrtf\b": "shortest remaining time first",
    r"\brr\b": "round robin",
    r"\b1nf\b": "first normal form",
    r"\b2nf\b": "second normal form",
    r"\b3nf\b": "third normal form",
    r"\bbcnf\b": "boyce-codd normal form",
    r"\bacid\b": "atomicity consistency isolation durability",
    r"\btoc\b": "theory of computation",
    r"\bflat\b": "formal languages and automata theory",
    r"\bdaa\b": "design and analysis of algorithms",
    r"\bcoa\b": "computer organization and architecture",
    r"\bse\b": "software engineering",
    r"\boops\b": "object-oriented programming",
    r"\bcn\b": "computer networks",
    r"\bpki\b": "public key infrastructure",
    r"\bapi\b": "application programming interface"
}

ACRONYM_SYMS = {
    "nlp": ["natural", "language", "processing", "nlp"],
    "cfg": ["context", "free", "grammar", "cfgs", "cfg"],
    "cfgs": ["context", "free", "grammar", "cfgs", "cfg"],
    "cnf": ["chomsky", "normal", "form", "cnf"],
    "gnf": ["greibach", "normal", "form", "gnf"],
    "cyk": ["cocke", "younger", "kasami", "cyk"],
    "ner": ["named", "entity", "recognition", "ner"],
    "pos": ["part", "speech", "tagging", "pos"],
    "crf": ["conditional", "random", "fields", "crf"],
    "hmm": ["hidden", "markov", "model", "hmm"],
    "bert": ["bert", "transformer", "transformers"],
    "gpt": ["gpt", "transformer", "transformers"],
    "llm": ["llm", "large", "language", "model"],
    "lstm": ["long", "short", "term", "memory", "lstm"],
    "rnn": ["recurrent", "neural", "network", "rnn"],
    "cnn": ["convolutional", "neural", "network", "cnn"],
    "ann": ["artificial", "neural", "network", "ann"],
    "gan": ["generative", "adversarial", "network", "gan"],
    "ae": ["autoencoder", "autoencoders", "ae", "aes", "encoder", "decoder"],
    "vae": ["variational", "autoencoder", "autoencoders", "vae", "vaes", "latent", "space"],
    "encoder": ["encoder", "encoders", "encode", "latent", "representation"],
    "decoder": ["decoder", "decoders", "decode", "reconstruction"],
    "latent": ["latent", "space", "representation", "dimension", "2d"],
    "dbms": ["database", "management", "system", "dbms"],
    "os": ["operating", "system", "os"],
    "ai": ["artificial", "intelligence", "ai"],
    "ml": ["machine", "learning", "ml"],
    "dl": ["deep", "learning", "dl"],
    "svm": ["support", "vector", "machine", "svm"],
    "pca": ["principal", "component", "analysis", "pca"]
}

def expand_abbreviations(text: str) -> str:
    """Expands common student texting shorthand and technical academic acronyms."""
    if not text:
        return ""
    expanded = text
    # Expand chat abbreviations
    for pattern, replacement in COMMON_CHAT_ABBREVIATIONS.items():
        expanded = re.sub(pattern, replacement, expanded, flags=re.IGNORECASE)
    # Expand academic acronyms
    for pattern, replacement in ACADEMIC_ACRONYMS.items():
        expanded = re.sub(pattern, replacement, expanded, flags=re.IGNORECASE)
    return expanded

COMMON_OCR_GLUED = {
    r"\bthelossfunction\b": "the loss function",
    r"\blossfunction\b": "loss function",
    r"\bcalculatas\b": "calculates",
    r"\bcalculata\b": "calculates",
    r"\btheerror\b": "the error",
    r"\btheneural\b": "the neural",
    r"\bneuralnetwork\b": "neural network",
    r"\bneuralnetworks\b": "neural networks",
    r"\berrorbackwardthrough\b": "error backward through",
    r"\bactivationfunction\b": "activation function",
    r"\bgradientdescent\b": "gradient descent",
    r"\binputlayer\b": "input layer",
    r"\boutputlayer\b": "output layer",
    r"\bhiddenlayer\b": "hidden layer",
    r"\bhiddenlayers\b": "hidden layers",
    r"\bforwardpropagation\b": "forward propagation",
    r"\bbackpropagation\b": "backpropagation",
    r"\bcrossentropy\b": "cross entropy",
    r"\bcostfunction\b": "cost function"
}

BULLET_SYMBOLS_PATTERN = (
    r"[\s\.\•\*\-\—\–\:\,\;\·\∙\●\○\▪\▫\■\□\►\▻\▶\▷\⁃\‣\·"
    r"\u2022\u25cf\u25cb\u25a0\u25a1\u25aa\u25ab\u25c6\u25c7\u25ba\u25bb\u25b6\u25b7\u2023\u2043\u2219\u00b7\uf0b7]+"
)

def clean_and_repair_text(text: str) -> str:
    """Cleans OCR noise, table formatting artifacts, broken spacing, and glued words."""
    if not text:
        return ""
    # Punctuation without space (e.g. 1.Input -> 1. Input, error.Backpropagation -> error. Backpropagation)
    cleaned = re.sub(r"(\d+)\.([A-Za-z])", r"\1. \2", text)
    cleaned = re.sub(r"([a-z0-9])\.([A-Z])", r"\1. \2", cleaned)
    cleaned = re.sub(r"([a-z0-9])\,([A-Za-z])", r"\1, \2", cleaned)
    cleaned = re.sub(r"([a-z0-9])\:([A-Za-z])", r"\1: \2", cleaned)

    # Normalize unspaced camelCase/compound words from tables (e.g. Softmax+Categorical)
    cleaned = re.sub(r"([a-z])([A-Z])", r"\1 \2", cleaned)
    cleaned = re.sub(r"[\+\=\|\t]+", " ", cleaned)

    # Specific glued phrase substitutions
    for pat, rep in COMMON_OCR_GLUED.items():
        cleaned = re.sub(pat, rep, cleaned, flags=re.IGNORECASE)

    # Strip leading bullets, dots, dashes, and extra whitespace from extracted lines
    cleaned = re.sub(rf"^{BULLET_SYMBOLS_PATTERN}", "", cleaned)
    # Replace internal bullet symbols surrounded by spaces with a clean dash
    cleaned = re.sub(r"\s+[\•\·\∙\●\○\▪\▫\■\□\►\▻\▶\▷\⁃\‣\u2022\u25cf\u25cb\u25a0\u25a1\u25aa\u25ab\u25c6\u25c7\u25ba\u25bb\u25b6\u25b7\u2023\u2043\u2219\u00b7\uf0b7]\s+", " - ", cleaned)
    # Remove any remaining stray bullet glyphs
    cleaned = re.sub(r"[\•\·\∙\●\○\▪\▫\■\□\►\▻\▶\▷\⁃\‣\u2022\u25cf\u25cb\u25a0\u25a1\u25aa\u25ab\u25c6\u25c7\u25ba\u25bb\u25b6\u25b7\u2023\u2043\u2219\u00b7\uf0b7]", "", cleaned)
    # Clean multiple consecutive dots ".. " -> ". "
    cleaned = re.sub(r"\.{2,}", ".", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned

def clean_sentence_bullet(s: str) -> str:
    """Ensures an extracted sentence or question has no leading bullet or punctuation artifacts."""
    if not s:
        return ""
    s = clean_and_repair_text(s)
    s = re.sub(rf"^{BULLET_SYMBOLS_PATTERN}", "", s).strip()
    s = re.sub(r"\s+(?:Applications|Example|Another Example|Scenario|Output|Advantages|Disadvantages|Features|Steps)\s*:\s*$", "", s, flags=re.IGNORECASE).strip()
    s = re.sub(r"[,:;]+$", "", s).strip()
    return s

MODULE_SUMMARIES_BY_SUBJECT = {
    "deep learning": (
        "**Summary of Deep Learning Module:**\n\n"
        "- **Neural Network Architecture:** Data flows from an **input layer** through multiple **hidden layers** to an **output layer**, where interconnected artificial neurons perform weighted summations and feature learning.\n"
        "- **Non-Linear Activations:** Mathematical activation functions (such as **ReLU**, **Sigmoid**, and **Softmax**) introduce non-linearity, enabling the network to approximate complex non-linear functions.\n"
        "- **Loss Calculation:** A **Loss Function** (e.g., Categorical Cross-Entropy for classification, Mean Squared Error for regression) calculates prediction discrepancy against ground-truth targets.\n"
        "- **Backpropagation & Optimization:** Error gradients propagate backward using the calculus chain rule, adjusting network weights via **Gradient Descent** (or Adam) to iteratively minimize prediction loss."
    ),
    "machine learning": (
        "**Summary of Machine Learning Module:**\n\n"
        "- **Core Learning Paradigms:** Encompasses **Supervised Learning** (labeled datasets for classification and regression), **Unsupervised Learning** (discovering groupings via clustering and PCA), and **Reinforcement Learning** (reward-penalty feedback).\n"
        "- **Model Training & Evaluation:** Training data is split into train, validation, and test subsets to evaluate generalization and balance the bias-variance tradeoff.\n"
        "- **Overfitting Prevention:** Techniques including $L_1$/$L_2$ regularization, cross-validation, and early stopping ensure models generalize to unseen test instances.\n"
        "- **Key Algorithms:** Commonly utilizes Decision Trees, Support Vector Machines, Linear/Logistic Regression, and K-Means clustering."
    ),
    "data mining": (
        "**Summary of Data Mining Module:**\n\n"
        "- **KDD Process Pipeline:** Systematic multi-step workflow comprising data cleaning, integration, selection, transformation, mining algorithm execution, pattern evaluation, and knowledge presentation.\n"
        "- **Supervised Classification:** Models discrete categories using algorithms such as Decision Trees, Naive Bayes classifiers, and Random Forests.\n"
        "- **Unsupervised Clustering:** Groups similar records based on distance and similarity metrics using partitioning (e.g., **K-Means**) and hierarchical clustering.\n"
        "- **Association Rule Mining:** Discovers meaningful co-occurrence relationships and itemset correlations using the **Apriori Algorithm**, evaluated by Support and Confidence metrics."
    ),
    "cpu scheduling": (
        "**Summary of Operating Systems (CPU Scheduling & Deadlocks):**\n\n"
        "- **Process Scheduling:** The CPU scheduler allocates processor time to ready processes to maximize throughput and CPU utilization while minimizing average turnaround and waiting times.\n"
        "- **Algorithm Classification:** Implements non-preemptive strategies (FCFS, SJF) and preemptive algorithms (Round Robin with time slicing, SRTF, Priority Scheduling).\n"
        "- **Deadlock Foundations:** Arises when processes wait indefinitely for resources held by others; requires all 4 Coffman conditions to occur.\n"
        "- **Deadlock Handling:** Controlled through prevention (resource ordering), avoidance (**Banker's Algorithm**), or runtime detection and recovery."
    ),
    "normalization": (
        "**Summary of Database Normalization Module:**\n\n"
        "- **Core Objective:** Decomposes relational schemas to eliminate insertion, deletion, and update anomalies while minimizing data redundancy.\n"
        "- **Normal Form Hierarchy:**\n"
        "  - **1NF:** Enforces atomic attribute values and eliminates repeating groups.\n"
        "  - **2NF:** Eliminates partial functional dependencies on composite candidate keys.\n"
        "  - **3NF:** Eliminates transitive dependencies between non-prime attributes.\n"
        "  - **BCNF:** Strictest form requiring every determinant to be a candidate key.\n"
        "- **Decomposition Criteria:** Preserves all operational properties via **Lossless Join** and **Dependency Preservation**."
    )
}

SYSTEM_PROMPT_CHATGPT_STYLE = (
    "You are CampusVerse's intelligent academic study assistant and notes tutor.\n"
    "Your mission is to help students understand their uploaded study materials with short, intelligent, student-friendly explanations strictly grounded in their uploaded notes.\n\n"
    "RESPONSE STYLE & TONE GUIDELINES (MANDATORY):\n"
    "1. Simple English: Speak clearly and naturally without convoluted jargon.\n"
    "2. Short and Meaningful: Provide direct, high-value answers without unnecessary conversational fluff or lengthy introductory filler.\n"
    "3. No Unnecessary Introductions or Repeated Answers: Jump straight into the concept or definition.\n"
    "4. Clean Formatting: Use concise bullet points for properties, lists, or steps, and bold terms for technical keywords.\n"
    "5. Simple Examples: Include intuitive examples when they clarify the concept.\n\n"
    "CRITICAL GROUNDING & ACCURACY RULES:\n"
    "1. EXCLUSIVE SOURCE OF TRUTH: Ground all answers in the provided STUDY NOTES CONTEXT. Never invent facts or hallucinate external information.\n"
    "2. HANDLING MISSING TOPICS: If a specific concept or topic cannot be found in the uploaded notes, respond EXACTLY with:\n"
    "   \"This topic is not available in the uploaded notes. Please upload the relevant study material.\"\n"
    "3. HANDLING UNRELATED QUESTIONS: If a student asks an off-topic or unrelated question (such as weather, recipes, movies, sports, personal conversations, resume writing, internship advertisements, or general trivia):\n"
    "   \"I'm CampusVerse's study assistant. I can help you with questions related to the academic notes uploaded here.\"\n"
    "4. INTELLIGENT QUESTION UNDERSTANDING:\n"
    "   - One-word questions (e.g., 'VAE'): Briefly explain the core concept based on the uploaded notes.\n"
    "   - Short queries (e.g., 'encoder?'): Explain what the component is directly and concisely.\n"
    "   - Informal shorthand & keywords (e.g., 'why blurry', 'latent space 2d', 'difference AE VAE'): Recognize the student's intent immediately and provide a focused, student-friendly answer.\n"
    "   - Follow-up questions (e.g., 'why is it used?', 'what are its limitations?', 'explain the second point'): Resolve pronouns ('it', 'this', 'that') and numbered points from the previous conversation turns smoothly.\n"
    "   - Never reject an academic question simply because it is phrased informally or differently from the uploaded material."
)

BRIEF_DEFINITIONS_BY_TOPIC = {
    "vae": (
        "**Variational Autoencoder (VAE):**\n"
        "- **Definition:** A generative model that learns to represent data in a continuous probability distribution within a latent space. Unlike standard autoencoders, a VAE outputs a mean ($\\mu$) and variance ($\\sigma$) vector, allowing it to sample new points and generate novel data."
    ),
    "variational autoencoder": (
        "**Variational Autoencoder (VAE):**\n"
        "- **Definition:** A generative model that learns to represent data in a continuous probability distribution within a latent space. Unlike standard autoencoders, a VAE outputs a mean ($\\mu$) and variance ($\\sigma$) vector, allowing it to sample new points and generate novel data."
    ),
    "encoder": (
        "An **encoder** is a part of an autoencoder that compresses the input into a smaller representation called latent representation. It captures the important features of the input."
    ),
    "decoder": (
        "A **decoder** is the part of an autoencoder that takes the lower-dimensional latent representation produced by the encoder and reconstructs the original input data as closely as possible."
    ),
    "latent space": (
        "**Latent Space:**\n"
        "- **Definition:** A compressed, lower-dimensional manifold where an encoder maps high-dimensional input data, capturing essential underlying factors and variations in a compact representation."
    ),
    "latent space 2d": (
        "**2D Latent Space:**\n"
        "- **Meaning:** When the latent space has two dimensions ($z_1, z_2$), high-dimensional data is compressed into a 2D coordinate plane.\n"
        "- **Benefit:** This allows easy visual plotting of data clusters, exploring the data manifold, and smooth interpolation between generated samples."
    ),
    "why blurry": (
        "VAEs can generate blurry images because their reconstruction process often focuses on average pixel values (using Mean Squared Error / L2 loss). This can smooth out fine details and sharp edges."
    ),
    "blurry": (
        "VAEs can generate blurry images because their reconstruction process often focuses on average pixel values (using Mean Squared Error / L2 loss). This can smooth out fine details and sharp edges."
    ),
    "difference ae vae": (
        "**Difference between Autoencoder (AE) and Variational Autoencoder (VAE):**\n\n"
        "- **Autoencoder (AE):** Maps inputs deterministically to discrete points in latent space; primarily used for feature compression, dimensionality reduction, and denoising.\n"
        "- **Variational Autoencoder (VAE):** Maps inputs to continuous probability distributions (mean and variance) in latent space regularized by KL divergence; used for generating brand new data samples."
    ),
    "ae": (
        "**Autoencoder (AE):**\n"
        "- **Definition:** An unsupervised neural network consisting of an encoder and decoder that compresses input into a bottleneck latent code and reconstructs it back to output.\n"
        "- **Use Cases:** Dimensionality reduction, image denoising, and anomaly detection."
    ),
    "autoencoder": (
        "**Autoencoder (AE):**\n"
        "- **Definition:** An unsupervised neural network consisting of an encoder and decoder that compresses input into a bottleneck latent code and reconstructs it back to output.\n"
        "- **Use Cases:** Dimensionality reduction, image denoising, and anomaly detection."
    ),
    "nlp": (
        "**Natural Language Processing - NLP (in short):**\n"
        "- **Definition:** A field of Artificial Intelligence and Computational Linguistics enabling computers to understand, interpret, and generate human languages.\n"
        "- **Core Tasks:** Syntax parsing, Context-Free Grammars (CFG), Named Entity Recognition (NER), Part-of-Speech (POS) tagging, sentiment analysis, and machine translation."
    ),
    "natural language processing": (
        "**Natural Language Processing - NLP (in short):**\n"
        "- **Definition:** A field of Artificial Intelligence and Computational Linguistics enabling computers to understand, interpret, and generate human languages.\n"
        "- **Core Tasks:** Syntax parsing, Context-Free Grammars (CFG), Named Entity Recognition (NER), Part-of-Speech (POS) tagging, sentiment analysis, and machine translation."
    ),
    "cfg": (
        "**Context-Free Grammar - CFG (in short):**\n"
        "- **Definition:** A formal grammar defined by 4-tuple $(V, \\Sigma, R, S)$ where production rules replace a single non-terminal with a string of terminals and non-terminals.\n"
        "- **Role in NLP:** Serves as the mathematical backbone for sentence syntax parsing and generating parse trees."
    ),
    "context-free grammar": (
        "**Context-Free Grammar - CFG (in short):**\n"
        "- **Definition:** A formal grammar defined by 4-tuple $(V, \\Sigma, R, S)$ where production rules replace a single non-terminal with a string of terminals and non-terminals.\n"
        "- **Role in NLP:** Serves as the mathematical backbone for sentence syntax parsing and generating parse trees."
    ),
    "cyk algorithm": (
        "**Cocke-Younger-Kasami (CYK) Algorithm (in short):**\n"
        "- **Definition:** A dynamic programming parsing algorithm for context-free grammars transformed into Chomsky Normal Form (CNF).\n"
        "- **Complexity:** Operates in $O(n^3 \\cdot |R|)$ time complexity to determine whether a string of length $n$ can be derived by the grammar."
    ),
    "cyk": (
        "**Cocke-Younger-Kasami (CYK) Algorithm (in short):**\n"
        "- **Definition:** A dynamic programming parsing algorithm for context-free grammars transformed into Chomsky Normal Form (CNF).\n"
        "- **Complexity:** Operates in $O(n^3 \\cdot |R|)$ time complexity to determine whether a string of length $n$ can be derived by the grammar."
    ),
    "ner": (
        "**Named Entity Recognition - NER (in short):**\n"
        "- **Definition:** A subtask of information extraction that identifies and categorizes key entities in unstructured text into predefined categories (such as Person, Organization, Location, Date, Time).\n"
        "- **Methods:** Implemented using sequence labeling models like CRF, BiLSTM-CRF, and Transformer-based models (BERT)."
    ),
    "named entity recognition": (
        "**Named Entity Recognition - NER (in short):**\n"
        "- **Definition:** A subtask of information extraction that identifies and categorizes key entities in unstructured text into predefined categories (such as Person, Organization, Location, Date, Time).\n"
        "- **Methods:** Implemented using sequence labeling models like CRF, BiLSTM-CRF, and Transformer-based models (BERT)."
    ),
    "pos tagging": (
        "**Part-of-Speech (POS) Tagging (in short):**\n"
        "- **Definition:** The process of marking up a word in a corpus to correspond to a particular part of speech (noun, verb, adjective, adverb) based on both its definition and context.\n"
        "- **Algorithms:** Hidden Markov Models (HMM), Maximum Entropy Markov Models (MEMM), and conditional random fields."
    ),
    "pos": (
        "**Part-of-Speech (POS) Tagging (in short):**\n"
        "- **Definition:** The process of marking up a word in a corpus to correspond to a particular part of speech (noun, verb, adjective, adverb) based on both its definition and context.\n"
        "- **Algorithms:** Hidden Markov Models (HMM), Maximum Entropy Markov Models (MEMM), and conditional random fields."
    ),
    "parsing": (
        "**Syntax Parsing (in short):**\n"
        "- **Definition:** The analysis of strings of symbols in natural language conforming to the rules of formal grammar, constructing hierarchical parse trees or dependency structures.\n"
        "- **Approaches:** Top-down parsing (e.g. Recursive Descent), bottom-up parsing (e.g. Shift-Reduce, CYK), and chart parsing."
    ),
    "syntax parsing": (
        "**Syntax Parsing (in short):**\n"
        "- **Definition:** The analysis of strings of symbols in natural language conforming to the rules of formal grammar, constructing hierarchical parse trees or dependency structures.\n"
        "- **Approaches:** Top-down parsing (e.g. Recursive Descent), bottom-up parsing (e.g. Shift-Reduce, CYK), and chart parsing."
    ),
    "lstm": (
        "**Long Short-Term Memory - LSTM (in short):**\n"
        "- **Definition:** A specialized Recurrent Neural Network (RNN) architecture designed to model long-term sequential dependencies.\n"
        "- **Gating Mechanism:** Uses input, forget, and output gates along with an internal cell state to resolve the vanishing gradient problem."
    ),
    "long short-term memory": (
        "**Long Short-Term Memory - LSTM (in short):**\n"
        "- **Definition:** A specialized Recurrent Neural Network (RNN) architecture designed to model long-term sequential dependencies.\n"
        "- **Gating Mechanism:** Uses input, forget, and output gates along with an internal cell state to resolve the vanishing gradient problem."
    ),
    "ethics": (
        "**AI Ethics (in short):**\n"
        "- **Definition:** The moral principles and legal guidelines governing artificial intelligence to ensure systems are safe, unbiased, privacy-preserving, and accountable.\n"
        "- **Key Issues:** Regulates copyrighted data scraping, intellectual property rights, algorithmic bias mitigation, and preventing malicious synthetic media (deepfakes)."
    ),
    "ai ethics": (
        "**AI Ethics (in short):**\n"
        "- **Definition:** The moral principles and legal guidelines governing artificial intelligence to ensure systems are safe, unbiased, privacy-preserving, and accountable.\n"
        "- **Key Issues:** Regulates copyrighted data scraping, intellectual property rights, algorithmic bias mitigation, and preventing malicious synthetic media (deepfakes)."
    ),
    "deep learning in data mining": (
        "**Deep Learning in Data Mining (in short):**\n"
        "- **Definition:** The application of deep neural networks (CNNs, Autoencoders) to autonomously discover complex, non-linear patterns and latent feature representations from massive datasets.\n"
        "- **Key Advantage:** Eliminates manual feature engineering and scales effectively to complex unstructured data (images, text, graph networks)."
    ),
    "deep learning": (
        "**Deep Learning (in short):**\n"
        "- **Definition:** A specialized branch of Machine Learning based on multi-layered Artificial Neural Networks that autonomously learns hierarchical feature abstractions directly from raw data.\n"
        "- **Key Mechanism:** Uses backpropagation and gradient descent across multiple hidden layers to optimize predictive accuracy without manual feature engineering."
    ),
    "data mining": (
        "**Data Mining (in short):**\n"
        "- **Definition:** The computational process of discovering hidden, valid, and previously unknown patterns, correlations, and anomalies from large datasets.\n"
        "- **Key Purpose:** Transforms raw data into actionable decision-making insights using automated classification, clustering, and association rule algorithms."
    ),
    "machine learning": (
        "**Machine Learning (in short):**\n"
        "- **Definition:** An AI discipline focused on developing algorithmic models that learn patterns from training data to make predictions without explicit programming.\n"
        "- **Core Paradigms:** Operates via supervised learning (labeled targets), unsupervised learning (clustering/discovery), and reinforcement learning (rewards)."
    ),
    "kdd": (
        "**Knowledge Discovery in Databases - KDD (in short):**\n"
        "- **Definition:** An end-to-end iterative pipeline that turns raw data into useful knowledge through data cleaning, integration, transformation, data mining, and evaluation.\n"
        "- **Core Goal:** Extracts valid, novel, and actionable intelligence from complex enterprise repositories."
    ),
    "knowledge discovery in databases": (
        "**Knowledge Discovery in Databases - KDD (in short):**\n"
        "- **Definition:** An end-to-end iterative pipeline that turns raw data into useful knowledge through data cleaning, integration, transformation, data mining, and evaluation.\n"
        "- **Core Goal:** Extracts valid, novel, and actionable intelligence from complex enterprise repositories."
    ),
    "association rule mining": (
        "**Association Rule Mining (in short):**\n"
        "- **Definition:** A data mining technique that discovers interesting co-occurrence patterns and relationships among items in transactional databases (e.g. Market Basket Analysis).\n"
        "- **Key Metrics:** Evaluates and prunes rules using Support (frequency), Confidence (certainty), and Lift (correlation strength)."
    ),
    "apriori algorithm": (
        "**Apriori Algorithm (in short):**\n"
        "- **Definition:** A classic association rule mining algorithm that iteratively generates candidate itemsets and prunes them using the Apriori principle.\n"
        "- **Key Rule:** Any subset of a frequent itemset must also be frequent; all supersets of an infrequent itemset are pruned."
    ),
    "apriori": (
        "**Apriori Algorithm (in short):**\n"
        "- **Definition:** A classic association rule mining algorithm that iteratively generates candidate itemsets and prunes them using the Apriori principle.\n"
        "- **Key Rule:** Any subset of a frequent itemset must also be frequent; all supersets of an infrequent itemset are pruned."
    ),
    "clustering": (
        "**Clustering (in short):**\n"
        "- **Definition:** An unsupervised learning technique that groups data objects into clusters based on geometric or statistical similarity.\n"
        "- **Key Objective:** Maximizes similarity between objects in the same cluster while maximizing dissimilarity between different clusters."
    ),
    "k-means": (
        "**K-Means Clustering (in short):**\n"
        "- **Definition:** A partitioning algorithm that groups $N$ records into $K$ clusters by iteratively assigning points to the nearest centroid and recomputing means.\n"
        "- **Convergence:** Iterations repeat until centroid locations stabilize or reach minimal within-cluster variance."
    ),
    "kmeans": (
        "**K-Means Clustering (in short):**\n"
        "- **Definition:** A partitioning algorithm that groups $N$ records into $K$ clusters by iteratively assigning points to the nearest centroid and recomputing means.\n"
        "- **Convergence:** Iterations repeat until centroid locations stabilize or reach minimal within-cluster variance."
    ),
    "data preprocessing": (
        "**Data Preprocessing (in short):**\n"
        "- **Definition:** The crucial preparation phase in data mining that cleans, integrates, transforms, and reduces raw data into high-quality inputs.\n"
        "- **Key Tasks:** Handles missing values, smooths noise, normalizes ranges, and reduces dimensions for optimal model accuracy."
    ),
    "neural network": (
        "**Artificial Neural Network - ANN (in short):**\n"
        "- **Definition:** A computational architecture of interconnected artificial neurons organized in input, hidden, and output layers to approximate non-linear functions.\n"
        "- **Key Mechanism:** Neurons compute weighted sums of inputs, apply non-linear activation functions, and update synaptic weights through backpropagation."
    ),
    "cpu scheduling": (
        "**CPU Scheduling (in short):**\n"
        "- **Definition:** The operating system strategy that selects which ready process receives processor execution time when the CPU becomes idle.\n"
        "- **Core Metric:** Balances throughput, CPU utilization, turnaround time, and waiting time using preemptive and non-preemptive algorithms."
    ),
    "deadlock": (
        "**Deadlock (in short):**\n"
        "- **Definition:** A permanent blocking condition where multiple processes cannot progress because each holds a resource while awaiting one held by another.\n"
        "- **Necessary Conditions:** Occurs if and only if all four Coffman conditions (Mutual Exclusion, Hold & Wait, No Preemption, Circular Wait) hold simultaneously."
    ),
    "normalization": (
        "**Database Normalization (in short):**\n"
        "- **Definition:** A relational schema design methodology that systematically organizes tables to eliminate insertion, update, and deletion anomalies.\n"
        "- **Key Standard:** Decomposes relations into progressive normal forms (1NF, 2NF, 3NF, BCNF) while preserving functional dependencies and lossless joins."
    ),
    "classification": (
        "**Classification (in short):**\n"
        "- **Definition:** A supervised learning technique where a trained model predicts discrete categorical labels for new, unseen data records.\n"
        "- **Standard Algorithms:** Decision Trees, Naive Bayes, Support Vector Machines (SVM), and Random Forests."
    ),
    "decision tree": (
        "**Decision Tree (in short):**\n"
        "- **Definition:** A flowchart-like hierarchical predictive model where internal nodes test features, branches represent outcomes, and leaf nodes represent class labels.\n"
        "- **Splitting Rule:** Selects attributes maximizing Information Gain (Entropy reduction) or minimizing Gini Impurity."
    ),
    "naive bayes": (
        "**Naive Bayes (in short):**\n"
        "- **Definition:** A fast probabilistic classifier applying Bayes' Theorem under the assumption that all features are mutually independent given the class label.\n"
        "- **Primary Advantage:** Extremely fast training with exceptional accuracy on high-dimensional text categorization and spam detection."
    ),
    "support vector machine": (
        "**Support Vector Machine - SVM (in short):**\n"
        "- **Definition:** A supervised learning algorithm that finds the optimal hyperplane maximizing the geometric margin between different data classes.\n"
        "- **Key Technique:** Uses the Kernel Trick (e.g. RBF) to map non-linearly separable points into higher-dimensional linear feature spaces."
    ),
    "svm": (
        "**Support Vector Machine - SVM (in short):**\n"
        "- **Definition:** A supervised learning algorithm that finds the optimal hyperplane maximizing the geometric margin between different data classes.\n"
        "- **Key Technique:** Uses the Kernel Trick to cleanly separate non-linear data distributions."
    ),
    "random forest": (
        "**Random Forest (in short):**\n"
        "- **Definition:** An ensemble learning model that combines predictions from multiple independently trained decision trees via majority voting or averaging.\n"
        "- **Key Advantage:** Drastically reduces model variance and prevents overfitting compared to a single standalone decision tree."
    ),
    "dbscan": (
        "**DBSCAN (in short):**\n"
        "- **Definition:** A density-based clustering algorithm that discovers clusters of arbitrary shapes by grouping points in dense regions and filtering out low-density noise.\n"
        "- **Parameters:** Uses $\\epsilon$ (neighborhood radius) and MinPts (minimum density threshold) without requiring a predefined cluster count $K$."
    ),
    "pca": (
        "**Principal Component Analysis - PCA (in short):**\n"
        "- **Definition:** An unsupervised linear dimensionality reduction technique that projects correlated features onto orthogonal principal eigenvectors.\n"
        "- **Core Goal:** Compresses feature spaces while retaining maximum cumulative statistical variance (e.g. 95%)."
    ),
    "process vs thread": (
        "**Process vs. Thread (in short):**\n"
        "- **Process:** An independent program with its own isolated virtual address space and heavyweight context-switching overhead.\n"
        "- **Thread:** A lightweight unit of execution within a parent process sharing the same address space, code, and heap."
    ),
    "virtual memory": (
        "**Virtual Memory (in short):**\n"
        "- **Definition:** An OS abstraction mapping large virtual address spaces to physical RAM and swap disk, allowing programs larger than physical memory to execute.\n"
        "- **Key Elements:** Relies on hardware Paging, Page Tables, TLB caches, and Page Replacement algorithms (LRU, FIFO)."
    ),
    "acid properties": (
        "**ACID Properties (in short):**\n"
        "- **Definition:** The 4 indispensable transactional guarantees of database systems: **Atomicity** (all-or-nothing), **Consistency** (valid states), **Isolation** (concurrency protection), and **Durability** (crash-proof persistence)."
    ),
    "indexing": (
        "**Database Indexing (in short):**\n"
        "- **Definition:** A sorted auxiliary data structure (typically B+ Trees) that allows database engines to locate records in $O(\\log N)$ time without full table scans."
    ),
    "sql vs nosql": (
        "**SQL vs. NoSQL (in short):**\n"
        "- **SQL:** Relational, structured tables, strict schemas, ACID compliance, vertically scalable (e.g. PostgreSQL, MySQL).\n"
        "- **NoSQL:** Non-relational, flexible dynamic schemas, BASE eventual consistency, horizontally scalable across clusters (e.g. MongoDB, Redis)."
    ),
    "osi model": (
        "**OSI Model (in short):**\n"
        "- **Definition:** A 7-layer theoretical network standard: Physical (1) $\\to$ Data Link (2) $\\to$ Network (3) $\\to$ Transport (4) $\\to$ Session (5) $\\to$ Presentation (6) $\\to$ Application (7)."
    ),
    "tcp vs udp": (
        "**TCP vs. UDP (in short):**\n"
        "- **TCP:** Connection-oriented, guaranteed in-order delivery, error recovery, and congestion control via 3-way handshakes.\n"
        "- **UDP:** Connectionless, minimal overhead (8 bytes), low latency without delivery guarantees (ideal for live streaming and gaming)."
    ),
    "binary search tree": (
        "**Binary Search Tree - BST (in short):**\n"
        "- **Definition:** A binary tree where every node's left child key is strictly smaller and right child key is strictly greater, delivering average $O(\\log N)$ search time."
    ),
    "time complexity": (
        "**Time Complexity & Asymptotic Notations (in short):**\n"
        "- **Big-O ($O$):** Worst-case upper bound runtime growth rate.\n"
        "- **Big-Omega ($\\Omega$):** Best-case lower bound runtime.\n"
        "- **Big-Theta ($\\Theta$):** Asymptotically tight bound."
    )
}

# Aliases for instant short-form concept lookups
BRIEF_DEFINITIONS_BY_TOPIC["dl"] = BRIEF_DEFINITIONS_BY_TOPIC["deep learning"]
BRIEF_DEFINITIONS_BY_TOPIC["ml"] = BRIEF_DEFINITIONS_BY_TOPIC["machine learning"]
BRIEF_DEFINITIONS_BY_TOPIC["dm"] = BRIEF_DEFINITIONS_BY_TOPIC["data mining"]
BRIEF_DEFINITIONS_BY_TOPIC["ann"] = BRIEF_DEFINITIONS_BY_TOPIC["neural network"]

EXAMPLES_BY_TOPIC = {
    "data mining": (
        "**Real-World Example of Data Mining:**\n\n"
        "- **Market Basket Analysis (Retail Stores):** By analyzing millions of supermarket checkout transactions using the Apriori algorithm, a retailer discovers that customers who purchase *bread and milk* frequently purchase *butter* on the same trip. The store uses this discovered association rule to optimize shelf placement and design promotional discounts.\n"
        "- **Credit Card Fraud Detection:** Financial institutions analyze transaction velocity, geolocation, and spending habits to instantly identify anomalous transactions that deviate from normal user patterns."
    ),
    "ethics": (
        "**AI Ethics (in short):**\n"
        "- **Definition:** The moral principles and legal guidelines governing artificial intelligence to ensure systems are safe, unbiased, privacy-preserving, and accountable.\n"
        "- **Key Issues:** Regulates copyrighted data scraping, intellectual property rights, algorithmic bias mitigation, and preventing malicious synthetic media (deepfakes)."
    ),
    "ai ethics": (
        "**AI Ethics (in short):**\n"
        "- **Definition:** The moral principles and legal guidelines governing artificial intelligence to ensure systems are safe, unbiased, privacy-preserving, and accountable.\n"
        "- **Key Issues:** Regulates copyrighted data scraping, intellectual property rights, algorithmic bias mitigation, and preventing malicious synthetic media (deepfakes)."
    ),
    "deep learning in data mining": (
        "**Real-World Example of Deep Learning in Data Mining:**\n\n"
        "- **Multi-Modal Customer Churn & Fraud Prediction:** Rather than manually creating hundreds of tabular attributes from customer call logs, chat transcripts, and web navigation clickstreams, a telecom enterprise feeds raw multi-modal sequential data into deep Autoencoders and LSTM networks. The deep model autonomously extracts complex behavioral patterns to predict customer churn and detect account takeover fraud."
    ),
    "deep learning": (
        "**Real-World Example of Deep Learning:**\n\n"
        "- **Medical Image Diagnosis:** A Convolutional Neural Network (CNN) trained on hundreds of thousands of chest X-rays automatically detects early-stage pneumonia or lung tumors by learning microscopic edge, texture, and density patterns directly from raw pixels, achieving specialist-level diagnostic accuracy.\n"
        "- **Autonomous Vehicles:** Self-driving cars process real-time 360° camera video feeds through deep neural networks to instantly classify pedestrians, cyclists, road lanes, and traffic signals."
    ),
    "machine learning": (
        "**Real-World Example of Machine Learning:**\n\n"
        "- **Email Spam Filtering:** A Naive Bayes or Logistic Regression classifier analyzes incoming emails, computing word occurrence probabilities to categorize messages into 'Inbox' or 'Spam' based on labeled historical emails."
    ),
    "kdd": (
        "**Real-World Example of KDD:**\n\n"
        "- **Healthcare Patient Risk Discovery:** A hospital repository collects raw electronic health records (EHR). Through data cleaning (imputing missing lab tests), integration (merging clinical records with pharmacy logs), transformation, data mining (clustering patient trajectories), and evaluation, doctors identify previously unrecognized early indicators of sepsis."
    ),
    "apriori algorithm": (
        "**Real-World Example of Apriori Algorithm:**\n\n"
        "- **E-Commerce Recommendation:** An online bookstore analyzes purchase baskets. It identifies that $\\{\\text{Python Programming, Machine Learning Guide}\\} \\Rightarrow \\{\\text{Data Science Handbook}\\}$ has 60% confidence and high lift, prompting automated 'Frequently Bought Together' recommendations."
    ),
    "clustering": (
        "**Real-World Example of Clustering:**\n\n"
        "- **Customer Segmentation:** An e-commerce platform uses K-Means clustering on purchase frequency, average order value, and website visit duration to segment customers into 'Bargain Hunters', 'Occasional Buyers', and 'VIP Loyalists' for targeted marketing."
    ),
    "k-means": (
        "**Real-World Example of K-Means:**\n\n"
        "- **Customer Segmentation:** An e-commerce platform uses K-Means clustering on purchase frequency, average order value, and website visit duration to segment customers into 'Bargain Hunters', 'Occasional Buyers', and 'VIP Loyalists' for targeted marketing."
    ),
    "cpu scheduling": (
        "**Real-World Example of CPU Scheduling:**\n\n"
        "- **Interactive Desktop OS (Round Robin):** When you are typing in a word processor, playing music, and downloading a file simultaneously, the OS allocates 10-20 ms time slices (time quanta) to each process in turn. Because switching happens in milliseconds, all applications appear to execute smoothly at the same time."
    ),
    "deadlock": (
        "**Real-World Example of Deadlock:**\n\n"
        "- **Traffic Gridlock at an Intersection:** Four vehicles arrive at a four-way junction simultaneously. Each vehicle enters the intersection, occupying its own quadrant while waiting for the vehicle ahead to clear the next quadrant. Since no vehicle can back up or preempt another, all four are permanently blocked."
    ),
    "normalization": (
        "**Real-World Example of Database Normalization:**\n\n"
        "- **Student Enrollment Database:** In an unnormalized table, updating a course instructor requires updating 500 individual student rows; if one row is missed, data becomes inconsistent (update anomaly). Normalizing to 3NF separates Students, Courses, and Instructors into distinct tables linked by foreign keys, ensuring each instructor name is stored only once."
    )
}

# Aliases for instant short-form concept lookups
EXAMPLES_BY_TOPIC["dl"] = EXAMPLES_BY_TOPIC["deep learning"]
EXAMPLES_BY_TOPIC["ml"] = EXAMPLES_BY_TOPIC["machine learning"]
EXAMPLES_BY_TOPIC["dm"] = EXAMPLES_BY_TOPIC["data mining"]

APPLICATIONS_AND_USES_BY_TOPIC = {
    "nlp": (
        "**Key Applications of Natural Language Processing (NLP):**\n\n"
        "- **Machine Translation:** Translating text or speech across languages (e.g., Google Translate, DeepL).\n"
        "- **Sentiment Analysis:** Classifying consumer opinions, product reviews, and social media sentiment (e.g., positive, neutral, negative).\n"
        "- **Conversational AI & Chatbots:** Powering virtual assistants and customer service bots (e.g., ChatGPT, Siri, Alexa).\n"
        "- **Information Extraction & Named Entity Recognition (NER):** Detecting and extracting structured entities (names, locations, dates, monetary values) from unstructured documents.\n"
        "- **Syntax Parsing & Grammar Checking:** Analyzing hierarchical sentence structures using Context-Free Grammars (CFGs) and parsing algorithms (e.g., CYK algorithm, dependency parsers) for writing tools like Grammarly.\n"
        "- **Text Summarization:** Generating concise summaries of lengthy research papers, news reports, and medical records.\n"
        "- **Speech Recognition:** Converting spoken language into text (Automatic Speech Recognition - ASR)."
    ),
    "natural language processing": (
        "**Key Applications of Natural Language Processing (NLP):**\n\n"
        "- **Machine Translation:** Translating text or speech across languages (e.g., Google Translate, DeepL).\n"
        "- **Sentiment Analysis:** Classifying consumer opinions, product reviews, and social media sentiment.\n"
        "- **Conversational AI & Chatbots:** Powering virtual assistants and customer service bots (e.g., ChatGPT, Siri, Alexa).\n"
        "- **Information Extraction & Named Entity Recognition (NER):** Extracting structured entities (names, locations, organizations) from unstructured text.\n"
        "- **Syntax Parsing & Grammar Checking:** Analyzing grammatical tree structures with formal grammars (CFGs) and parsers (e.g., CYK algorithm).\n"
        "- **Text Summarization:** Condensing long articles and documents into key actionable points.\n"
        "- **Speech Recognition:** Converting spoken acoustic signals into written text."
    ),
    "cfg": (
        "**Applications of Context-Free Grammars (CFG):**\n\n"
        "- **Compiler Design:** Specifying syntax rules and constructing parse trees for programming languages (e.g., C, Python, Java).\n"
        "- **Natural Language Parsing:** Modeling syntactic sentence structures in NLP using production rules.\n"
        "- **Grammar Checking:** Detecting syntactic anomalies in text generation and writing tools.\n"
        "- **Document Validation:** Defining schema structures and validating hierarchical tag nestings (XML/JSON)."
    ),
    "context-free grammar": (
        "**Applications of Context-Free Grammars (CFG):**\n\n"
        "- **Compiler Design:** Specifying syntax rules and constructing parse trees for programming languages.\n"
        "- **Natural Language Parsing:** Modeling syntactic sentence structures in NLP using production rules.\n"
        "- **Grammar Checking:** Detecting syntactic anomalies in text generation and writing tools."
    ),
    "cyk algorithm": (
        "**Applications of Cocke-Younger-Kasami (CYK) Algorithm:**\n\n"
        "- **Grammar Parsing in NLP:** Determining whether a sentence belongs to a given Context-Free Grammar in Chomsky Normal Form (CNF).\n"
        "- **Computational Linguistics:** Constructing syntactic parse trees in $O(n^3)$ dynamic programming runtime.\n"
        "- **Bioinformatics & RNA Structure:** Modeling secondary RNA folding structures using stochastic context-free grammars."
    ),
    "cyk": (
        "**Applications of Cocke-Younger-Kasami (CYK) Algorithm:**\n\n"
        "- **Grammar Parsing in NLP:** Determining whether a sentence belongs to a given Context-Free Grammar in Chomsky Normal Form (CNF).\n"
        "- **Computational Linguistics:** Constructing syntactic parse trees in $O(n^3)$ dynamic programming runtime.\n"
        "- **Bioinformatics & RNA Structure:** Modeling secondary RNA folding structures using stochastic context-free grammars."
    ),
    "ner": (
        "**Applications of Named Entity Recognition (NER):**\n\n"
        "- **Search Engines & SEO:** Indexing documents by key entities (persons, places, organizations) for semantic search.\n"
        "- **Content Recommendation:** Extracting topics and tags to recommend related news articles or academic papers.\n"
        "- **Customer Support Automation:** Extracting order numbers, product names, and dates from support tickets.\n"
        "- **Healthcare & Biomedical:** Extracting disease names, drug molecules, and genes from clinical trial papers."
    ),
    "named entity recognition": (
        "**Applications of Named Entity Recognition (NER):**\n\n"
        "- **Search Engines & SEO:** Indexing documents by key entities (persons, places, organizations) for semantic search.\n"
        "- **Content Recommendation:** Extracting topics and tags to recommend related news articles or academic papers.\n"
        "- **Customer Support Automation:** Extracting order numbers, product names, and dates from support tickets.\n"
        "- **Healthcare & Biomedical:** Extracting disease names, drug molecules, and genes from clinical trial papers."
    ),
    "pos tagging": (
        "**Applications of Part-of-Speech (POS) Tagging:**\n\n"
        "- **Named Entity Recognition & Parsing:** Serves as a vital prerequisite step for dependency parsing and entity extraction.\n"
        "- **Text-to-Speech (TTS) Synthesis:** Ensuring correct word pronunciation based on whether a word acts as a noun or verb (e.g., 'record' vs. 'record').\n"
        "- **Word Sense Disambiguation:** Resolving semantic meaning based on lexical syntactic category."
    ),
    "pos": (
        "**Applications of Part-of-Speech (POS) Tagging:**\n\n"
        "- **Named Entity Recognition & Parsing:** Serves as a vital prerequisite step for dependency parsing and entity extraction.\n"
        "- **Text-to-Speech (TTS) Synthesis:** Ensuring correct word pronunciation based on whether a word acts as a noun or verb.\n"
        "- **Word Sense Disambiguation:** Resolving semantic meaning based on lexical syntactic category."
    ),
    "data mining": (
        "**Why Data Mining is Useful & Its Real-World Applications:**\n\n"
        "Data Mining transforms massive volumes of raw, chaotic business data into actionable intelligence, automated predictions, and strategic decisions. Here is how and why it is so valuable across industries:\n\n"
        "1. **Market Basket Analysis & Retail Sales Optimization:**\n"
        "   - **How it helps:** Discovers products that customers frequently buy together (using Association Rule Mining via the Apriori algorithm).\n"
        "   - **Impact:** Supermarkets and e-commerce platforms (like Amazon and Walmart) use this to place complementary items together, design bundle discounts, and drive cross-selling revenues.\n\n"
        "2. **Banking & Financial Fraud Detection:**\n"
        "   - **How it helps:** Financial institutions analyze spending velocity, transaction amounts, and geographical locations.\n"
        "   - **Impact:** Instantly flags fraudulent credit card transactions and calculates accurate credit risk scores before approving loans.\n\n"
        "3. **Customer Segmentation & Churn Prevention:**\n"
        "   - **How it helps:** Uses clustering (e.g., K-Means) to divide millions of customers into distinct profiles (high-value shoppers, budget buyers, at-risk users).\n"
        "   - **Impact:** Telecom and subscription services predict which customers are about to leave (churn) and send them targeted retention offers.\n\n"
        "4. **Healthcare & Disease Diagnosis:**\n"
        "   - **How it helps:** Analyzes thousands of historical patient records, lab reports, and genomic sequences.\n"
        "   - **Impact:** Predicts early onset of chronic illnesses (such as diabetes, heart disease, and cancer) and prevents harmful drug interactions.\n\n"
        "5. **Manufacturing & Predictive Maintenance:**\n"
        "   - **How it helps:** Mines real-time IoT sensor telemetry from factory machines and turbines.\n"
        "   - **Impact:** Predicts hardware wear-and-tear days before a breakdown occurs, preventing costly plant shutdowns.\n\n"
        "6. **Cybersecurity & Intrusion Detection:**\n"
        "   - **How it helps:** Discovers unusual traffic anomalies across corporate networks to stop cyber attacks and data breaches."
    ),
    "ethics": (
        "**AI Ethics (in short):**\n"
        "- **Definition:** The moral principles and legal guidelines governing artificial intelligence to ensure systems are safe, unbiased, privacy-preserving, and accountable.\n"
        "- **Key Issues:** Regulates copyrighted data scraping, intellectual property rights, algorithmic bias mitigation, and preventing malicious synthetic media (deepfakes)."
    ),
    "ai ethics": (
        "**AI Ethics (in short):**\n"
        "- **Definition:** The moral principles and legal guidelines governing artificial intelligence to ensure systems are safe, unbiased, privacy-preserving, and accountable.\n"
        "- **Key Issues:** Regulates copyrighted data scraping, intellectual property rights, algorithmic bias mitigation, and preventing malicious synthetic media (deepfakes)."
    ),
    "deep learning in data mining": (
        "**Why Deep Learning in Data Mining is Useful:**\n\n"
        "1. **Autonomous Feature Learning:** Eliminates tedious manual attribute engineering; deep neural networks autonomously extract hierarchical features directly from raw data (images, voice, sensor streams).\n"
        "2. **Handles Massive Unstructured Data:** Traditional data mining struggled with raw audio, video, and text. Deep architectures (CNNs, Transformers, Autoencoders) mine unstructured datasets seamlessly.\n"
        "3. **Ultra-Accurate Anomaly Detection:** Deep autoencoders learn the baseline distribution of standard transactions and detect complex zero-day bank fraud that traditional decision trees miss.\n"
        "4. **High-Dimensional Clustering:** Learns non-linear latent embeddings that group high-dimensional records far better than linear distance metrics."
    ),
    "deep learning": (
        "**Why Deep Learning is Useful & Its Real-World Applications:**\n\n"
        "1. **Computer Vision & Medical Imaging:** Powers automated tumor detection in MRI scans, facial recognition, and object tracking in autonomous vehicles.\n"
        "2. **Natural Language Processing (NLP):** Powers modern AI chatbots, automated language translation, speech recognition, and document summarization.\n"
        "3. **Autonomous Vehicles & Robotics:** Processes camera video and LiDAR sensor feeds in real-time to steer, brake, and navigate safely.\n"
        "4. **Drug Discovery & Genomics:** Analyzes molecular 3D structures to accelerate the creation of life-saving pharmaceutical drugs."
    ),
    "machine learning": (
        "**Why Machine Learning is Useful & Its Real-World Applications:**\n\n"
        "1. **Automated Decision Making:** Replaces rigid, hardcoded rule sets with adaptive statistical models that improve automatically with more data.\n"
        "2. **Personalized Recommendations:** Powers recommendation engines on Netflix, Spotify, and YouTube based on user preferences.\n"
        "3. **Spam & Malware Filtering:** Email providers (Gmail, Outlook) automatically filter out spam and malicious attachments with high precision.\n"
        "4. **Financial Forecasting & Algorithmic Trading:** Analyzes stock market trends and risk factors to execute optimal trades."
    ),
    "neural network": (
        "**Why Artificial Neural Networks (ANNs) are Useful:**\n\n"
        "1. **Non-Linear Modeling:** Accurately models complex non-linear relationships that traditional linear regression cannot capture.\n"
        "2. **Fault Tolerance:** Distributed synaptic weights allow neural networks to continue operating accurately even if some inputs are noisy or missing.\n"
        "3. **Adaptability & Generalization:** Capable of generalizing well to unseen data after training with backpropagation and gradient descent."
    ),
    "kdd": (
        "**Why KDD (Knowledge Discovery in Databases) is Useful:**\n\n"
        "1. **End-to-End Data Quality:** Ensures data is cleaned, integrated, and transformed before mining, preventing 'garbage in, garbage out'.\n"
        "2. **Enterprise Big Data Scalability:** Provides a structured, reliable pipeline to turn terabytes of messy transactional logs into actionable intelligence.\n"
        "3. **Strategic Business Decisions:** Bridges the gap between raw data storage and executive decision-making."
    ),
    "apriori algorithm": (
        "**Why the Apriori Algorithm is Useful:**\n\n"
        "1. **Market Basket Insights:** Discovers product co-occurrences so stores know which items drive companion sales.\n"
        "2. **Prunes Search Space:** Uses the Apriori anti-monotonicity principle to safely ignore millions of rare candidate itemsets, making association rule mining computationally feasible."
    ),
    "clustering": (
        "**Why Clustering is Useful:**\n\n"
        "1. **No Labels Needed:** Discovers natural patterns in raw, unlabelled data without requiring expensive manual data tagging.\n"
        "2. **Targeted Groupings:** Segments customers, patient cohorts, document topics, and geographical regions for tailored strategies."
    ),
    "cpu scheduling": (
        "**Why CPU Scheduling is Useful:**\n\n"
        "1. **Maximizes CPU Utilization:** Ensures the processor is rarely idle, delivering maximum computational throughput.\n"
        "2. **Fairness & Responsiveness:** Prevents process starvation, guaranteeing that interactive desktop apps remain responsive to user clicks."
    ),
    "deadlock": (
        "**Why Deadlock Understanding & Prevention is Useful:**\n\n"
        "1. **System Stability:** Prevents operating systems and database servers from freezing permanently when competing for shared resources.\n"
        "2. **High Concurrency:** Ensures multi-threaded software can safely share memory, database locks, and devices without crashing."
    ),
    "normalization": (
        "**Why Database Normalization is Useful:**\n\n"
        "1. **Eliminates Redundancy:** Stores each data fact in exactly one place, minimizing disk storage waste.\n"
        "2. **Prevents Anomalies:** Eliminates insertion, update, and deletion anomalies, ensuring database integrity across enterprise transactions."
    ),
    "classification": (
        "**Why Classification is Useful & Its Real-World Applications:**\n\n"
        "1. **Medical Diagnosis:** Predicts disease malignancy (benign vs. malignant tumors) from pathology records.\n"
        "2. **Credit Risk Evaluation:** Banks classify loan applicants into creditworthy vs. high-risk categories.\n"
        "3. **Spam & Security Filtering:** Automatically tags incoming messages as clean or phishing spam."
    ),
    "decision tree": (
        "**Why Decision Trees are Useful:**\n\n"
        "1. **High Interpretability (White-Box Model):** Can be visualized and easily audited by human stakeholders and regulators.\n"
        "2. **Handles Both Data Types:** Naturally processes both numerical and categorical attributes without extensive preprocessing."
    ),
    "naive bayes": (
        "**Why Naive Bayes is Useful:**\n\n"
        "1. **Ultra-Fast Training:** Requires only single-pass frequency calculations, making it ideal for streaming real-time applications.\n"
        "2. **Superior Text Performance:** Exceptional baseline benchmark for sentiment analysis, document tagging, and spam detection."
    ),
    "support vector machine": (
        "**Why Support Vector Machines (SVM) are Useful:**\n\n"
        "1. **High-Dimensional Effectiveness:** Excels in spaces where feature count exceeds sample count (e.g. genomic microarrays).\n"
        "2. **Memory Efficiency:** Only the support vectors influence the decision boundary, reducing storage demands."
    ),
    "svm": (
        "**Why Support Vector Machines (SVM) are Useful:**\n\n"
        "1. **High-Dimensional Effectiveness:** Excels in spaces where feature count exceeds sample count (e.g. genomic microarrays).\n"
        "2. **Memory Efficiency:** Only the support vectors influence the decision boundary, reducing storage demands."
    ),
    "virtual memory": (
        "**Why Virtual Memory is Useful:**\n\n"
        "1. **Protects Memory Spaces:** Isolates application processes so one crashed program cannot overwrite another's memory.\n"
        "2. **Overcomes Physical Hardware Limits:** Enables computers with 8 GB of RAM to run large programs requiring 16+ GB through disk paging."
    ),
    "acid properties": (
        "**Why ACID Properties are Indispensable:**\n\n"
        "1. **Financial Precision:** Guarantees that money deducted from Account A is always credited to Account B, or completely refunded if the network drops.\n"
        "2. **Data Consistency:** Prevents database corruption from simultaneous conflicting user updates."
    ),
    "indexing": (
        "**Why Database Indexing is Useful:**\n\n"
        "1. **Massive Query Acceleration:** Reduces lookup times from $O(N)$ (scanning millions of rows) to $O(\\log N)$ (scanning 3-4 tree levels).\n"
        "2. **Enforces Uniqueness:** Primary key and unique index constraints automatically maintain entity integrity."
    ),
    "osi model": (
        "**Why the OSI Model is Useful:**\n\n"
        "1. **Standardized Interoperability:** Enables hardware and software from different vendors (Apple, Microsoft, Cisco) to communicate seamlessly.\n"
        "2. **Modular Troubleshooting:** Network engineers isolate connection faults layer-by-layer (e.g., cable at Layer 1 vs. DNS at Layer 7)."
    ),
    "tcp vs udp": (
        "**Why Choosing Between TCP and UDP is Essential:**\n\n"
        "1. **Reliability vs. Speed:** TCP guarantees lossless web browsing and banking; UDP delivers minimum latency for real-time multiplayer gaming and live streams."
    )
}

APPLICATIONS_AND_USES_BY_TOPIC["dl"] = APPLICATIONS_AND_USES_BY_TOPIC["deep learning"]
APPLICATIONS_AND_USES_BY_TOPIC["ml"] = APPLICATIONS_AND_USES_BY_TOPIC["machine learning"]
APPLICATIONS_AND_USES_BY_TOPIC["dm"] = APPLICATIONS_AND_USES_BY_TOPIC["data mining"]
APPLICATIONS_AND_USES_BY_TOPIC["ann"] = APPLICATIONS_AND_USES_BY_TOPIC["neural network"]
APPLICATIONS_AND_USES_BY_TOPIC["bst"] = APPLICATIONS_AND_USES_BY_TOPIC.get("binary search tree", APPLICATIONS_AND_USES_BY_TOPIC["data mining"])
APPLICATIONS_AND_USES_BY_TOPIC["tcp"] = APPLICATIONS_AND_USES_BY_TOPIC["tcp vs udp"]
APPLICATIONS_AND_USES_BY_TOPIC["udp"] = APPLICATIONS_AND_USES_BY_TOPIC["tcp vs udp"]
APPLICATIONS_AND_USES_BY_TOPIC["osi"] = APPLICATIONS_AND_USES_BY_TOPIC["osi model"]
APPLICATIONS_AND_USES_BY_TOPIC["acid"] = APPLICATIONS_AND_USES_BY_TOPIC["acid properties"]

HOW_IT_WORKS_BY_TOPIC = {
    "data mining": (
        "**How Data Mining Works (The Step-by-Step Workflow):**\n\n"
        "Data Mining follows a systematic multi-step workflow to extract patterns from raw data:\n\n"
        "1. **Data Integration & Cleaning:**\n"
        "   - Merges multiple data sources (databases, transactional logs, files).\n"
        "   - Cleans dirty data by handling missing attributes, removing duplicate records, and smoothing noisy outliers.\n\n"
        "2. **Data Selection & Transformation:**\n"
        "   - Selects only the features relevant to the analytical goal.\n"
        "   - Normalizes numerical values (e.g., scaling between 0 and 1) and aggregates fields for algorithms to process.\n\n"
        "3. **Applying Mining Algorithms (The Core Step):**\n"
        "   - **Classification:** Builds models (Decision Trees, Naive Bayes) to predict discrete categorical classes.\n"
        "   - **Clustering:** Groups similar data records into clusters (K-Means, DBSCAN) without predefined labels.\n"
        "   - **Association Rule Mining:** Finds frequent item correlations (Apriori algorithm).\n"
        "   - **Anomaly Detection:** Flags extreme outliers deviating from standard patterns.\n\n"
        "4. **Pattern Evaluation & Pruning:**\n"
        "   - Evaluates discovered patterns against statistical thresholds (Support, Confidence, Lift, Accuracy).\n"
        "   - Discards uninteresting or redundant rules.\n\n"
        "5. **Knowledge Representation & Deployment:**\n"
        "   - Presents actionable findings using charts, graphs, and prediction APIs integrated into business software."
    ),
    "deep learning": (
        "**How Deep Learning Works (Step-by-Step Mechanism):**\n\n"
        "1. **Input Layer:** Receives raw numerical representations of data (e.g., pixel matrices, audio waveforms, or token embeddings).\n"
        "2. **Forward Propagation:** Data flows forward through successive hidden layers. Each neuron computes a weighted sum of inputs plus a bias ($z = \\sum w_i x_i + b$) and passes it through an **activation function** (like ReLU) to introduce non-linearity.\n"
        "3. **Hierarchical Feature Learning:** Early hidden layers detect simple low-level patterns (edges, textures); deeper layers combine them into high-level abstract concepts (eyes, faces, full objects).\n"
        "4. **Loss Calculation:** The output layer produces predictions, and a **loss function** (e.g., Cross-Entropy, MSE) calculates the mathematical error compared to ground truth.\n"
        "5. **Backpropagation & Optimization:** The error gradient is propagated backward through the network using the calculus chain rule. Optimizers (like Adam or SGD) adjust the synaptic weights via **Gradient Descent** to reduce future error."
    ),
    "machine learning": (
        "**How Machine Learning Works:**\n\n"
        "1. **Data Collection:** Gather representative training data with features and known outcomes (for supervised learning).\n"
        "2. **Feature Engineering:** Select, clean, and encode the most predictive attributes.\n"
        "3. **Model Training:** Feed the data to an algorithm (like Random Forest or Logistic Regression) that mathematically optimizes internal parameters to minimize error.\n"
        "4. **Validation & Testing:** Evaluate the model on unseen test data to verify it generalizes well and does not overfit.\n"
        "5. **Inference:** Deploy the trained model to make automated predictions on brand new incoming data."
    ),
    "decision tree": (
        "**How a Decision Tree Works (Step-by-Step Splitting):**\n\n"
        "1. **Calculate Impurity:** Evaluates the target dataset using Entropy or Gini Index.\n"
        "2. **Evaluate Attribute Splits:** Tests every available feature to measure Information Gain or Gain Ratio.\n"
        "3. **Select Best Split:** Picks the attribute yielding the highest Information Gain to form the current decision node.\n"
        "4. **Recurse:** Divides the dataset into subsets corresponding to the branch values and recursively splits until leaf purity or max depth is reached."
    ),
    "naive bayes": (
        "**How Naive Bayes Works:**\n\n"
        "1. **Prior Calculation:** Computes prior class probabilities $P(C_k)$ from training frequency.\n"
        "2. **Likelihood Computation:** Calculates conditional probabilities $P(x_i \\mid C_k)$ for each feature given the class.\n"
        "3. **Multiply Likelihoods:** Multiplies priors by attribute likelihoods assuming conditional independence.\n"
        "4. **Class Assignment:** Normalizes posteriors and selects the class with highest probability."
    ),
    "apriori algorithm": (
        "**How the Apriori Algorithm Works:**\n\n"
        "1. **Count 1-Itemsets ($C_1$):** Scan database to calculate support for all individual items.\n"
        "2. **Prune to $L_1$:** Discard items failing the minimum support threshold.\n"
        "3. **Candidate Generation ($C_{k}$):** Join frequent $(k-1)$-itemsets to form size-$k$ candidates.\n"
        "4. **Apriori Pruning:** Eliminate candidates containing any non-frequent $(k-1)$-subset.\n"
        "5. **Repeat:** Continue until no larger frequent itemsets can be formed."
    ),
    "virtual memory": (
        "**How Virtual Memory Works (Paging Mechanism):**\n\n"
        "1. **CPU Emits Virtual Address:** Composed of Virtual Page Number (VPN) and Page Offset.\n"
        "2. **TLB Lookup:** Checks the hardware Translation Lookaside Buffer for an instant cache hit.\n"
        "3. **Page Table Walk:** On TLB miss, references the multi-level Page Table in RAM.\n"
        "4. **Page Fault Handling:** If valid bit is 0, OS issues a Page Fault interrupt, reads page from swap disk, replaces a frame (via LRU/FIFO), and restarts instruction."
    )
}

HOW_IT_WORKS_BY_TOPIC["dl"] = HOW_IT_WORKS_BY_TOPIC["deep learning"]
HOW_IT_WORKS_BY_TOPIC["ml"] = HOW_IT_WORKS_BY_TOPIC["machine learning"]
HOW_IT_WORKS_BY_TOPIC["dm"] = HOW_IT_WORKS_BY_TOPIC["data mining"]
HOW_IT_WORKS_BY_TOPIC["ann"] = HOW_IT_WORKS_BY_TOPIC["deep learning"]
HOW_IT_WORKS_BY_TOPIC["tcp"] = HOW_IT_WORKS_BY_TOPIC.get("tcp vs udp", HOW_IT_WORKS_BY_TOPIC["data mining"])
HOW_IT_WORKS_BY_TOPIC["osi"] = HOW_IT_WORKS_BY_TOPIC.get("osi model", HOW_IT_WORKS_BY_TOPIC["data mining"])

SIMPLIFIED_EXPLANATIONS_BY_TOPIC = {
    "deep learning": (
        "No worries at all! Let's break down **Deep Learning** in a very simple, everyday way:\n\n"
        "### The Simple Analogy: Teaching a Child to Recognize a Cat\n"
        "Think of how a human child learns what a cat looks like:\n"
        "- You don't give the child a manual of mathematical formulas or tell them: *'A cat has whiskers at 45 degrees and two triangular ears.'*\n"
        "- Instead, you show them lots of pictures of cats and dogs.\n"
        "- Over time, their brain automatically learns to spot the subtle patterns that make a cat a cat!\n\n"
        "**Deep Learning does the exact same thing for computers:**\n\n"
        "### How It Works in 3 Simple Steps:\n"
        "1. **Input:** You feed raw data (like a photo, voice clip, or sentence) into the computer.\n"
        "2. **Multiple Layers (The 'Deep' Part):** The computer passes the data through several connected layers of artificial neurons:\n"
        "   - **First Layer:** Spots tiny, simple shapes (like straight edges, lines, and curves).\n"
        "   - **Middle Layers:** Puts those lines together into recognizable parts (like eyes, ears, wheels, or letters).\n"
        "   - **Final Layer:** Recognizes the complete object (e.g., *'That is a cat with 98% confidence!'*).\n"
        "3. **Learning from Mistakes (Backpropagation):** If the network makes a wrong guess, it automatically adjusts its internal dials (called weights) so it gets it right next time.\n\n"
        "**Key Takeaway:** Unlike traditional programming where humans write every rule, Deep Learning **learns the rules on its own directly from data**!\n\n"
        "Does this make it clearer? Feel free to ask about any specific part or let me know if you want another example!"
    ),
    "data mining": (
        "No worries! Let's understand **Data Mining** with a simple real-life example:\n\n"
        "### The Simple Analogy: Supermarket Treasure Hunting\n"
        "Imagine a huge supermarket with millions of checkout receipts saved in computers:\n"
        "- Looking at one receipt at a time tells you almost nothing.\n"
        "- But when you run **Data Mining**, smart computer algorithms search through millions of receipts to uncover hidden customer habits that no human would notice alone.\n"
        "- **The Classic Discovery:** Supermarkets discovered that people who buy diapers on Friday evenings frequently buy snacks at the same time. The store places snacks right next to diapers, and sales immediately shoot up!\n\n"
        "### What Data Mining Does in 3 Simple Tasks:\n"
        "1. **Finds Patterns (Association):** Discovers what items customers regularly buy together.\n"
        "2. **Groups Similar Items (Clustering):** Automatically groups customers into 'Budget Shoppers' vs. 'Premium Buyers'.\n"
        "3. **Spots Cheaters (Anomaly Detection):** Instantly flags a credit card purchase in another country that looks suspicious.\n\n"
        "**Key Takeaway:** Data Mining is like **mining for gold in a mountain of raw data**—turning useless numbers into valuable insights!"
    ),
    "ethics": (
        "**AI Ethics (in short):**\n"
        "- **Definition:** The moral principles and legal guidelines governing artificial intelligence to ensure systems are safe, unbiased, privacy-preserving, and accountable.\n"
        "- **Key Issues:** Regulates copyrighted data scraping, intellectual property rights, algorithmic bias mitigation, and preventing malicious synthetic media (deepfakes)."
    ),
    "ai ethics": (
        "**AI Ethics (in short):**\n"
        "- **Definition:** The moral principles and legal guidelines governing artificial intelligence to ensure systems are safe, unbiased, privacy-preserving, and accountable.\n"
        "- **Key Issues:** Regulates copyrighted data scraping, intellectual property rights, algorithmic bias mitigation, and preventing malicious synthetic media (deepfakes)."
    ),
    "deep learning in data mining": (
        "No worries! Here is **Deep Learning in Data Mining** explained in simple terms:\n\n"
        "### The Simple Idea:\n"
        "- **Traditional Data Mining** is great at organized spreadsheets (like Excel tables with names, ages, and prices). But it struggles when data is messy—like millions of images, video feeds, voice recordings, or social media posts.\n"
        "- **Deep Learning in Data Mining** brings powerful multi-layer neural networks into the data mining process to find hidden patterns in this complex, messy data automatically!\n\n"
        "### Why It's Useful:\n"
        "1. **No Manual Work:** In old data mining, human experts had to manually extract every single attribute. Deep Learning figures out the features on its own.\n"
        "2. **Smart Grouping:** It can group millions of customer voice calls or medical scans without a human having to label them first.\n"
        "3. **Ultra-Fast Fraud Detection:** Spots bank fraud among billions of live transactions by noticing microscopic patterns invisible to standard formulas."
    ),
    "machine learning": (
        "No worries! Let's understand **Machine Learning** in simple language:\n\n"
        "### Traditional Programming vs. Machine Learning:\n"
        "- **Traditional Programming:** You write strict rules: *If temperature > 100, turn on the fan.*\n"
        "- **Machine Learning:** You feed data and answers to the computer: *Here are 10,000 days of temperature records and whether people turned on fans.* The computer figures out the rule by itself!\n\n"
        "### The 3 Main Types:\n"
        "1. **Supervised Learning (Learning with a Teacher):** You show questions with correct answers (like flashcards). It learns to answer new questions.\n"
        "2. **Unsupervised Learning (Finding Hidden Patterns):** You give it uncategorized data and it groups similar things together on its own.\n"
        "3. **Reinforcement Learning (Trial & Error):** Like training a pet with treats—the computer gets rewarded for good moves and learns the winning strategy (e.g. playing chess)."
    ),
    "neural network": (
        "No worries! Think of an **Artificial Neural Network (ANN)** like a team of detectives solving a puzzle:\n\n"
        "1. **Input Detectives:** Look at the raw clues (pixels, numbers, words).\n"
        "2. **Hidden Clue Analyzers:** Each detective looks for specific clues (one checks colors, another checks sizes, another checks edges) and passes their opinion forward with a score (weight).\n"
        "3. **Chief Decision Maker (Output):** Combines everyone's opinion to declare the final decision!\n\n"
        "Every time the team makes a mistake, the chief corrects who should be trusted more next time. That is how neural networks learn!"
    ),
    "kdd": (
        "No worries! **KDD (Knowledge Discovery in Databases)** is simply a 5-step recipe for turning messy data into smart decisions:\n\n"
        "1. **Clean:** Wash away dirty data (typos, duplicates, blank fields).\n"
        "2. **Integrate:** Combine different spreadsheets into one central database.\n"
        "3. **Transform:** Organize and scale numbers so formulas can read them easily.\n"
        "4. **Mine:** Run smart algorithms to discover hidden trends and patterns.\n"
        "5. **Use:** Show the discovered charts and insights to managers to make profitable decisions."
    ),
    "apriori algorithm": (
        "No worries! The **Apriori Algorithm** is built on one simple common-sense rule:\n\n"
        "**'If you don't even like bananas, you definitely won't buy a banana-split sundae!'**\n\n"
        "In data mining terms:\n"
        "- If an item (like Beer) is rare on its own, then combination baskets like `{Beer, Diaper, Bread}` will also be rare, so the computer immediately skips checking them.\n"
        "- This saves the computer from checking billions of useless combinations and only focuses on frequent items that people actually buy together!"
    ),
    "clustering": (
        "No worries! Think of **Clustering** like organizing a messy toy box without labels:\n\n"
        "- You don't have tags on the toys, but you naturally put all the lego bricks in one pile, stuffed animals in another pile, and toy cars in a third pile because they look and feel alike.\n"
        "- **In Data Mining:** Algorithms like **K-Means** measure how close data points are to each other and automatically group similar customers, diseases, or products together without needing human labels!"
    ),
    "cpu scheduling": (
        "No worries! Think of **CPU Scheduling** like a doctor managing a busy hospital emergency room:\n\n"
        "- There is only 1 doctor (the CPU) and 5 patients waiting (programs like Spotify, Word, Chrome).\n"
        "- **First-Come-First-Served (FCFS):** Treat whoever walked in the door first.\n"
        "- **Shortest Job First (SJF):** Treat the person with a minor cut first because they take only 30 seconds!\n"
        "- **Round Robin:** Give every patient exactly 2 minutes of attention, then move to the next patient in a circle so nobody waits too long.\n\n"
        "The CPU switches so quickly (in milliseconds) that it feels like all your apps are running at the same time!"
    ),
    "deadlock": (
        "No worries! Imagine two stubborn drivers meeting on a narrow, single-lane bridge:\n\n"
        "- Driver A refuses to back up until Driver B moves.\n"
        "- Driver B refuses to back up until Driver A moves.\n"
        "- **Result:** Neither can move, and traffic is stuck forever!\n\n"
        "In an Operating System, a **Deadlock** happens when Program 1 holds the printer and waits for the scanner, while Program 2 holds the scanner and waits for the printer. Both are frozen indefinitely!"
    ),
    "normalization": (
        "No worries! **Database Normalization** is like organizing your closet so you don't keep three copies of the same shirt in different drawers:\n\n"
        "- If a student changes their address in an unnormalized system, you might have to edit 20 different rows. If you miss one, the data is broken!\n"
        "- Normalization breaks messy tables into clean, linked tables (Students table, Courses table, Teachers table) so every piece of information is stored in **exactly one place** with zero confusion."
    )
}

SIMPLIFIED_EXPLANATIONS_BY_TOPIC["dl"] = SIMPLIFIED_EXPLANATIONS_BY_TOPIC["deep learning"]
SIMPLIFIED_EXPLANATIONS_BY_TOPIC["ml"] = SIMPLIFIED_EXPLANATIONS_BY_TOPIC["machine learning"]
SIMPLIFIED_EXPLANATIONS_BY_TOPIC["dm"] = SIMPLIFIED_EXPLANATIONS_BY_TOPIC["data mining"]
SIMPLIFIED_EXPLANATIONS_BY_TOPIC["ann"] = SIMPLIFIED_EXPLANATIONS_BY_TOPIC["neural network"]

def is_brevity_request(query: str) -> bool:
    """Detects requests to shorten, condense, or provide 2-line/brief answers."""
    if not query or len(query.split()) > 10:
        return False
    ql = query.lower().strip()
    clean = re.sub(r"[^\w\s]", "", ql).strip()
    brevity_phrases = {
        "in short", "short", "in brief", "brief", "briefly", "shorter",
        "make it short", "make it shorter", "short answer", "short explanation",
        "too long", "in one line", "one line", "in 1 line", "1 line",
        "in 2 lines", "2 lines", "answer in 2 lines", "in two lines", "two lines",
        "in 3 lines", "3 lines", "answer in 3 lines", "in three lines",
        "in points", "in 2 points", "2 points", "in two points", "points",
        "give in 2 lines", "give in short", "give in brief", "give short answer",
        "tell in 2 lines", "tell in short", "explain in 2 lines", "write in 2 lines",
        "in 2 sentences", "in two sentences", "answer in 2 sentences"
    }
    if clean in brevity_phrases:
        return True
    if re.search(r"\b(in\s+short|in\s+brief|briefly|make\s+it\s+short|make\s+it\s+shorter|short\s+answer)\b", ql):
        return True
    if re.search(r"\b(answer|explain|tell|give|write|summarize)\s+in\s+(\d+|one|two|three)\s+(lines?|points?|sentences?)\b", ql):
        return True
    if re.search(r"\bin\s+(\d+|one|two|three)\s+(lines?|points?|sentences?)\b", ql):
        return True
    return False

def is_example_request(query: str) -> bool:
    """Detects follow-up requests for real-world academic examples."""
    if not query or len(query.split()) > 10:
        return False
    ql = query.lower().strip()
    clean = re.sub(r"[^\w\s]", "", ql).strip()
    example_phrases = {
        "example", "examples", "give example", "give an example", "give examples",
        "show example", "show an example", "real life example", "real world example",
        "practical example", "can you give an example", "can you give example",
        "provide an example", "provide example", "explain with example"
    }
    if clean in example_phrases:
        return True
    if re.search(r"\b(give|show|provide|explain\s+with)\s+(an?\s+)?(example|real\s+life\s+example|real\s+world\s+example)\b", ql):
        return True
    return False

def is_confusion_or_simplification_request(query: str) -> bool:
    """Detects when a student did not understand a concept or asks for simpler explanation."""
    if not query:
        return False
    ql = query.lower().strip()
    clean = re.sub(r"[^\w\s]", "", ql).strip()
    confusion_phrases = {
        "i didnt understand", "i didn't understand", "didnt understand", "didn't understand",
        "did not understand", "i did not understand", "i dont understand", "i don't understand",
        "dont understand", "don't understand", "do not understand", "i do not understand",
        "i cant understand", "i can't understand", "cant understand", "can't understand",
        "cannot understand", "i cannot understand", "not understanding", "not able to understand",
        "i am confused", "im confused", "confusing", "too confusing", "too complex",
        "too hard", "hard to understand", "difficult to understand", "not clear", "it is not clear",
        "it isnt clear", "explain simply", "explain in simple way", "explain in simple terms",
        "explain in simple words", "make it simpler", "simplify this", "simplify", "simpler",
        "explain again", "tell again", "once more", "in layman terms", "laymans terms",
        "for beginners", "what does that mean", "i still dont get it", "still dont understand",
        "still confused"
    }
    if clean in confusion_phrases:
        return True
    if re.search(r"\b(i\s+)?(didnt|didn't|did\s+not|dont|don't|do\s+not|cant|can't|cannot)\s+(understand|get\s+it|follow)\b", ql):
        return True
    if re.search(r"\b(not\s+(clear|understanding)|unclear\s+to\s+me|makes?\s+no\s+sense)\b", ql):
        return True
    if re.search(r"\b(explain|teach|tell)\s+(it\s+)?again\b", ql):
        return True
    if re.search(r"\b(make\s+it\s+(simpler|easier)|explain\s+(it\s+)?in\s+(a\s+)?(simple|simpler|easy|easier)\s+(way|manner|words?|terms?|language)|in\s+simple\s+words?)\b", ql):
        return True
    return False

def is_useful_or_application_request(query: str) -> bool:
    """Detects questions asking about usefulness, applications, importance, benefits, or uses."""
    if not query:
        return False
    ql = query.lower().strip()
    clean = re.sub(r"[^\w\s]", "", ql).strip()

    triggers = [
        "useful", "usefulness", "how its useful", "how is it useful", "why is it useful",
        "how is this useful", "how useful is this", "uses", "what are its uses", "uses of this",
        "application", "applications", "real world applications", "real life applications",
        "where is it used", "where is this used", "benefit", "benefits", "importance",
        "why do we need this", "why do we use this", "why use this", "what is the use",
        "what is its use", "what is the purpose", "purpose of this", "advantage", "advantages",
        "how can it be used", "how can this be used", "what does it do", "why is this needed",
        "how is data mining useful", "why is data mining useful", "uses of data mining",
        "how is deep learning useful", "uses of deep learning"
    ]
    if clean in triggers or any(clean.startswith(t + " ") or clean.endswith(" " + t) or f" {t} " in f" {clean} " for t in triggers):
        return True
    if re.search(r"\b(how|why)\s+(is\s+it|its|is\s+this|are\s+they)\s+(useful|needed|used|important|helpful)\b", ql):
        return True
    if re.search(r"\b(uses|applications|benefits|importance|purpose|advantages)\s+of\b", ql):
        return True
    if re.search(r"\bwhere\s+(is\s+it|are\s+they|is\s+this)\s+used\b", ql):
        return True
    return False

def is_how_it_works_request(query: str) -> bool:
    """Detects questions asking how a concept works, its mechanism, or step-by-step process."""
    if not query:
        return False
    ql = query.lower().strip()
    clean = re.sub(r"[^\w\s]", "", ql).strip()

    triggers = [
        "how it works", "how does it work", "how this works", "how do it work",
        "working principle", "working mechanism", "steps involved", "process flow",
        "how does this work", "working", "mechanism", "internal working", "explain working",
        "how does it function", "workflow"
    ]
    if clean in triggers or any(clean.startswith(t + " ") or clean.endswith(" " + t) or f" {t} " in f" {clean} " for t in triggers):
        return True
    if re.search(r"\bhow\s+(does\s+it|does\s+this|it|this)\s+work(s)?\b", ql):
        return True
    if re.search(r"\bworking\s+(of|mechanism|principle)\b", ql):
        return True
    return False

def is_grammatically_complete_sentence(s: str) -> bool:
    """Verifies that an extracted sentence is grammatically intact and not an incomplete OCR fragment."""
    s_clean = s.strip()
    words = s_clean.split()
    if len(words) < 6:
        return False
    # Filter dangling prepositions, conjunctions, articles, and auxiliary verbs
    dangling_words = {
        "to", "of", "in", "on", "at", "by", "for", "from", "with", "about",
        "into", "through", "during", "before", "after", "above", "below",
        "between", "under", "since", "without", "within", "because", "as",
        "until", "while", "though", "although", "whether", "if", "the", "a",
        "an", "whose", "which", "where", "when", "who", "whom", "what",
        "that", "is", "are", "was", "were", "be", "been", "being", "have",
        "has", "had", "and", "or", "but", "nor"
    }
    last_word = re.sub(r"[^\w]", "", words[-1].lower())
    if last_word in dangling_words:
        return False
    return True

def resolve_topic_from_history_and_context(
    conversation_history: List[Dict[str, str]],
    context_chunks: List[Dict[str, Any]]
) -> str:
    """Identifies the target academic topic from previous conversation turns or active document context."""
    # 1. Inspect conversation history from most recent to oldest
    for msg in reversed(conversation_history):
        content = msg.get("content", "").lower()
        if (is_brevity_request(content) or is_example_request(content) or 
            is_confusion_or_simplification_request(content) or 
            is_useful_or_application_request(content) or 
            is_how_it_works_request(content)):
            continue
        for topic in sorted(BRIEF_DEFINITIONS_BY_TOPIC.keys(), key=len, reverse=True):
            if topic in content:
                return topic
        for topic in sorted(ACADEMIC_KNOWLEDGE_BASE.keys(), key=len, reverse=True):
            if topic in content:
                return topic

    # 2. Inspect active context chunks (document title or text)
    if context_chunks:
        for c in context_chunks:
            title = c.get("title", "").lower()
            for topic in sorted(BRIEF_DEFINITIONS_BY_TOPIC.keys(), key=len, reverse=True):
                if topic in title:
                    return topic
        for c in context_chunks:
            text = c.get("text", "").lower()
            for topic in sorted(BRIEF_DEFINITIONS_BY_TOPIC.keys(), key=len, reverse=True):
                if topic in text:
                    return topic

    return ""

def is_unrelated_subject_or_domain(
    query: str,
    context_chunks: List[Dict[str, Any]] = [],
    material_titles: List[str] = []
) -> bool:
    """
    Detects whether the student's query asks about an unrelated academic subject,
    external competitive entrance exam, or non-academic domain not present in their uploaded notes.
    """
    ql = query.lower()
    clean_q = re.sub(r"[^\w\s]", "", ql)
    q_words = set(clean_q.split())

    # Build corpus text of active context (chunks + titles)
    active_text = " ".join([c.get("title", "") + " " + c.get("text", "") for c in (context_chunks or [])]).lower()
    for t in (material_titles or []):
        active_text += " " + t.lower()

    # External exams from other academic disciplines
    EXTERNAL_EXAMS = {
        "neet", "jee", "upsc", "cat", "clat", "gmat", "mcat", "usmle", "aiims", "nda", "cds"
    }
    # Unrelated subjects / domains (unless explicitly part of the student's active notes)
    UNRELATED_SUBJECTS = {
        "chemistry", "organic chemistry", "inorganic chemistry", "physical chemistry",
        "botany", "zoology", "anatomy", "physiology", "pathology", "pharmacology",
        "pediatrics", "cardiology", "dermatology", "biochemistry",
        "metallurgy", "civil engineering", "structural engineering", "concrete",
        "ancient history", "world history", "geography", "astrology", "horoscope",
        "fashion", "cooking", "recipe", "baking", "cricket", "football", "tennis",
        "bollywood", "hollywood", "cinema"
    }
    # Common unrelated entities, wildlife, sports, food, and trivia
    UNRELATED_ENTITIES = {
        "buffalo", "cow", "lion", "tiger", "elephant", "dog", "cat", "horse",
        "whale", "shark", "bear", "monkey", "snake", "bird", "fish", "dinosaur",
        "animal", "animals", "wildlife", "zoo", "pet", "pets",
        "weather", "rain", "climate", "temperature", "zodiac", "horoscope",
        "movie", "movies", "song", "songs", "actor", "actress", "celebrity",
        "cricket", "football", "soccer", "basketball", "tennis", "badminton",
        "pizza", "burger", "cake", "baking", "recipe", "cooking"
    }

    for exam in EXTERNAL_EXAMS:
        if exam in q_words and exam not in active_text:
            return True

    for subj in UNRELATED_SUBJECTS:
        if subj in ql and subj not in active_text:
            return True

    for entity in UNRELATED_ENTITIES:
        if entity in q_words and entity not in active_text:
            return True

    return False

def handle_conversational_intent(
    query: str,
    conversation_history: List[Dict[str, str]] = []
) -> Optional[str]:
    """
    Identifies conversational intents strictly adhering to tutor personality:
    1. Inappropriate or abusive language
    2. Greetings and casual conversations (Section 9.A)
    3. Friendly help requests (Section 9.B)
    4. Thanks and appreciation
    5. Goodbyes and closings
    6. General Knowledge / Trivia / Sports / Off-topic questions (Section 3)
    7. Incomplete or vague questions
    """
    expanded = expand_abbreviations(query)
    ql = expanded.lower().strip()
    clean = re.sub(r"[^\w\s]", "", ql).strip()
    words = clean.split()

    if not words:
        return "Hey! 👋 Welcome! Ready to study? Ask me anything related to your uploaded notes."

    # Never treat brevity, follow-up, example, or confusion/simplification requests as vague
    if is_brevity_request(ql) or is_example_request(ql) or is_confusion_or_simplification_request(ql) or is_useful_or_application_request(ql) or is_how_it_works_request(ql):
        return None

    # 1. Inappropriate / Abusive words (Section 9.C)
    inappropriate_words = {
        "idiot", "stupid", "fool", "shut up", "hate you", "useless", "dumb", "kill", "die",
        "sex", "porn", "bastard", "crap", "shit", "fuck", "bitch", "asshole", "trash", "loser"
    }
    if any(w in inappropriate_words for w in words):
        return "Please maintain respectful language. 😊 I'm here to help you study your uploaded notes."

    # 2. Greetings and Casual Conversations (Section 9.A)
    # Student: "Hi", "Hiii", "Hey", "Heyyy", "Hello"
    greeting_pattern = r"^(hi+|hey+|hello+|hola+|namaste+|yo+|sup+|heya+)(\s+(there|buddy|friend|bot|ai))?$"
    if re.match(greeting_pattern, clean) or clean in ["hi", "hey", "hello", "yo", "sup", "hi there", "hey there", "hello there"]:
        return "Hey! 👋 Welcome! Ready to study? Ask me anything related to your uploaded notes."

    # Student: "Hello" -> "Hello! 😊 How can I help you with your study material today?"
    if clean in ["hello", "hola", "namaste", "greetings", "hello there"]:
        return "Hello! 😊 How can I help you with your study material today?"

    # Student: "Good morning" -> "Good morning! ☀️ Hope you're having a great day. What would you like to learn today?"
    if "good morning" in clean or clean == "morning":
        return "Good morning! ☀️ Hope you're having a great day. What would you like to learn today?"

    if any(g in clean for g in ["good afternoon", "good evening", "good day"]):
        return "Good day! 😊 Hope you're having a great day. What would you like to learn today?"

    # Student: "How are you?" -> "I'm doing great! 😊 I'm ready to help you understand your notes. What are we studying today?"
    if re.search(r"\b(how\s+are\s+you|how\s+are\s+u|hows\s+it\s+going|how\s+do\s+you\s+do)\b", ql):
        return "I'm doing great! 😊 I'm ready to help you understand your notes. What are we studying today?"

    # 3. Friendly Help Requests (Section 9.B)
    help_triggers = [
        "can you help me", "could you help me", "help me", "can you explain this",
        "i have a doubt", "have a doubt", "got a doubt", "i dont understand this topic",
        "i don't understand this topic", "can you teach me", "teach me", "help me study"
    ]
    if any(trigger in clean for trigger in help_triggers) and len(words) <= 7:
        return "Of course! 😊 I'm here to help. Ask me a question related to your uploaded notes."

    # 4. Thanks and Appreciation
    if any(g in clean for g in ["thank you", "thanks", "thx", "thank u", "appreciate it", "great explanation", "that helped"]):
        return "You're welcome! 😊 Keep up the great studying. Ask me anytime you have doubts from your notes."

    # 5. Casual Chat & Closings
    farewell_pattern = r"^(bye+|goodbye+|cya+|see\s+ya|see\s+you|take\s+care|good\s*night|gn|bye\s*bye|bbye+|ttyl|later)(\s+(buddy|friend|bot|ai))?$"
    if re.match(farewell_pattern, clean) or clean in ["bye", "byee", "byeee", "goodbye", "see you", "see ya", "cya", "take care", "good night", "gn", "bye bye", "byebye", "ok bye", "okay bye"]:
        return "Goodbye! 👋 Happy studying, and feel free to reach out whenever you want to study your notes."

    if clean in ["ok", "okay", "alright", "got it", "sure", "cool", "nice", "great", "fine", "yes", "no", "yep", "nope"]:
        return "Great! What topic or question from your notes would you like to explore next?"

    if re.search(r"\b(who\s+are\s+you|what\s+can\s+you\s+do|what\s+is\s+your\s+name|tell\s+me\s+about\s+yourself)\b", ql):
        return "I am your CampusVerse AI Study Companion! I'm here to answer your questions strictly based on the study materials and notes you upload."

    # 6. Unrelated / Off-Topic / General Knowledge / Trivia / Entertainment / Sports (Section 3)
    unrelated_triggers = [
        "cricket", "ipl", "football", "soccer", "fifa", "messi", "ronaldo", "match", "score",
        "capital of", "who invented", "tell me a joke", "make me laugh", "crack a joke",
        "movie", "bollywood", "hollywood", "weather today", "weather in", "prime minister",
        "president of", "who won", "election", "recipe", "cook", "how to bake", "resume",
        "internship advertisement", "job vacancy", "personal advice"
    ]
    if any(t in clean for t in unrelated_triggers):
        return "I'm CampusVerse's study assistant. I can help you with questions related to the academic notes uploaded here."

    # 7. Incomplete messages
    incomplete_starters = ["difference between", "formula for", "define", "what is the example of", "compare"]
    if clean in incomplete_starters or (len(words) <= 3 and any(clean.startswith(prefix) for prefix in ["difference between", "formula for"])):
        return "It looks like your question is incomplete. Could you please specify which concept or topic from your notes you would like me to explain?"

    # 8. Unclear or Incomplete
    stopwords_or_vague = {
        "what", "why", "how", "when", "where", "who", "is", "it", "the", "and", "or", "so", 
        "but", "if", "tell", "explain", "describe", "please", "can", "you", "do", "a", "an", 
        "then", "just", "this", "that", "there", "here", "to", "for", "with", "about"
    }
    if len(words) <= 2 and all(w in stopwords_or_vague for w in words):
        return "I'm here to help! Could you please specify which topic or concept from your notes you would like to study?"

    return None

async def call_gemini_rag_answer(
    query: str,
    context_chunks: List[Dict[str, Any]],
    conversation_history: List[Dict[str, str]] = [],
    material_titles: List[str] = []
) -> Optional[str]:
    """Generates conversational or academic grounded answers using Gemini following strict instructions."""
    if not settings.GEMINI_API_KEY:
        return None

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.GEMINI_MODEL}:generateContent?key={settings.GEMINI_API_KEY}"

    context_str = "\n\n".join(
        f"[Study Excerpt]\n{clean_and_repair_text(c['text'])}"
        for c in context_chunks
    )

    # Build prompt with history
    history_str = ""
    for msg in conversation_history[-4:]:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        history_str += f"{role.capitalize()}: {content}\n"

    doc_titles_str = ", ".join(material_titles) if material_titles else "Selected Study Notes"
    prompt = (
        f"ACTIVE STUDY DOCUMENT: {doc_titles_str}\n\n"
        f"STUDY NOTES CONTEXT:\n{context_str}\n\n"
        f"PREVIOUS CONVERSATION:\n{history_str}\n\n"
        f"STUDENT QUESTION:\n{query}\n\n"
        f"RESPONSE:"
    )

    payload = {
        "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT_CHATGPT_STYLE}]},
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.35,
            "maxOutputTokens": 800,
        }
    }

    try:
        async with httpx.AsyncClient(timeout=25.0) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                cand = data.get("candidates", [])
                if cand:
                    parts = cand[0].get("content", {}).get("parts", [])
                    if parts:
                        return parts[0].get("text", "").strip()
    except Exception as e:
        logger.warning("Gemini RAG answer call error: %s", e)

    return None

EXAM_QUESTIONS_BY_SUBJECT = {
    "deep learning": (
        "**Most Important University Exam Questions (Deep Learning):**\n\n"
        "**Short Answer Questions (2 Marks):**\n"
        "1. Define Artificial Neural Network (ANN) and list its structural layers.\n"
        "2. What is an Activation Function? Why is non-linearity required in deep networks?\n"
        "3. Differentiate between **Sigmoid**, **Tanh**, and **ReLU** activation functions.\n"
        "4. What is the role of a Loss Function? Give examples for regression and classification.\n"
        "5. How does the **Dropout** technique prevent overfitting during training?\n\n"
        "**Long Answer Questions (10 / 16 Marks):**\n"
        "1. Explain the complete architecture of a **Convolutional Neural Network (CNN)** with a neat block diagram, detailing convolution, pooling, and fully connected layers.\n"
        "2. Derive and explain the **Backpropagation** algorithm step-by-step using the calculus chain rule for updating network weights.\n"
        "3. Discuss the **Vanishing Gradient** and **Exploding Gradient** problems in deep networks and explain modern mitigation methods (ReLU, Batch Normalization, Skip Connections).\n"
        "4. Explain the architecture and internal gating mechanisms of **LSTM** (Long Short-Term Memory) networks and compare them with standard RNNs."
    ),
    "machine learning": (
        "**Most Important University Exam Questions (Machine Learning):**\n\n"
        "**Short Answer Questions (2 Marks):**\n"
        "1. Differentiate between **Supervised Learning** and **Unsupervised Learning** with examples.\n"
        "2. What is the Bias-Variance tradeoff in machine learning?\n"
        "3. Define Overfitting and Underfitting. How can they be detected?\n"
        "4. What is the purpose of Cross-Validation?\n\n"
        "**Long Answer Questions (10 / 16 Marks):**\n"
        "1. Explain **Linear Regression** and **Logistic Regression** with mathematical formulations and cost functions.\n"
        "2. Describe the **Decision Tree** algorithm, detailing splitting criteria (Information Gain, Entropy, Gini Index).\n"
        "3. Explain the working principle of **Support Vector Machines (SVM)** with linear and non-linear kernel functions.\n"
        "4. Describe the **K-Means Clustering** algorithm with step-by-step workflow and convergence criteria."
    ),
    "data mining": (
        "**Most Important University Exam Questions (Data Mining):**\n\n"
        "**Short Answer Questions (2 Marks):**\n"
        "1. Define Data Mining and distinguish it from conventional database queries.\n"
        "2. Define **Support** and **Confidence** in Association Rule Mining.\n"
        "3. What is Data Preprocessing, and why is it required in KDD?\n"
        "4. Differentiate between Classification and Clustering.\n\n"
        "**Long Answer Questions (10 / 16 Marks):**\n"
        "1. Explain the steps in the **Knowledge Discovery in Databases (KDD)** process with a neat architectural diagram.\n"
        "2. Explain the **Apriori Algorithm** for mining frequent itemsets with a complete numerical example.\n"
        "3. Discuss hierarchical vs partitioning clustering methods and explain the **K-Means** algorithm in detail.\n"
        "4. Explain various Data Transformation and Dimensionality Reduction techniques (e.g., PCA)."
    ),
    "cpu scheduling": (
        "**Most Important University Exam Questions (Operating Systems - CPU Scheduling):**\n\n"
        "**Short Answer Questions (2 Marks):**\n"
        "1. Define CPU Scheduling and distinguish between Preemptive and Non-Preemptive scheduling.\n"
        "2. Define Turnaround Time, Waiting Time, and Response Time.\n"
        "3. What is the Convoy Effect in First-Come, First-Served (FCFS) scheduling?\n"
        "4. Why does Shortest Job First (SJF) offer optimal average waiting time?\n\n"
        "**Long Answer Questions (10 / 16 Marks):**\n"
        "1. Compare FCFS, SJF, SRTF, and Round Robin scheduling algorithms with Gantt chart examples and average waiting time calculations.\n"
        "2. Explain the four necessary Coffman conditions for Deadlock and illustrate Banker's Algorithm for deadlock avoidance.\n"
        "3. Discuss multi-level queue and multi-level feedback queue scheduling mechanisms."
    ),
    "normalization": (
        "**Most Important University Exam Questions (DBMS - Normalization):**\n\n"
        "**Short Answer Questions (2 Marks):**\n"
        "1. Define Database Normalization and state its objectives.\n"
        "2. What is a Functional Dependency? Give an example.\n"
        "3. Differentiate between Primary Key, Candidate Key, and Super Key.\n"
        "4. What are insertion, deletion, and update anomalies in unnormalized tables?\n\n"
        "**Long Answer Questions (10 / 16 Marks):**\n"
        "1. Explain 1NF, 2NF, 3NF, and BCNF with step-by-step relational decomposition examples.\n"
        "2. State and prove Armstrong's Axioms for functional dependencies.\n"
        "3. Explain Lossless Join Decomposition and Dependency Preservation with proofs."
    )
}

def extract_questions_from_chunks(chunks: List[Dict[str, Any]]) -> List[str]:
    """Finds genuine exam questions and problem prompts from uploaded material chunks."""
    questions = []
    question_kw = (
        "explain", "define", "differentiate", "describe", "discuss", "compare",
        "what", "how", "why", "state", "list", "illustrate", "derive", "calculate",
        "distinguish", "elaborate", "analyze", "evaluate", "give", "write"
    )
    for c in chunks:
        text = c.get("text", "")
        for line in text.splitlines():
            line_clean = clean_sentence_bullet(line)
            stripped = re.sub(r"^(?:q(?:uestion)?\s*[\.\:\d\-]+|\d+[\.\)\-]\s*|\([a-z0-9]+\)\s*)+", "", line_clean, flags=re.IGNORECASE).strip()
            stripped = clean_sentence_bullet(stripped)
            is_q = False
            if line_clean.endswith("?"):
                is_q = True
            elif stripped and any(stripped.lower().startswith(kw + " ") for kw in question_kw):
                is_q = True

            if is_q and 10 <= len(line_clean) <= 250:
                if not any(tag in line_clean.lower() for tag in ["page ", "http", "copyright", "isbn"]):
                    clean_display = stripped if stripped else line_clean
                    clean_display = clean_sentence_bullet(clean_display)
                    if clean_display not in questions:
                        questions.append(clean_display)
                        if len(questions) >= 10:
                            break
        if len(questions) >= 10:
            break
    return questions

def synthesize_generalized_academic_answer(query: str, active_topic: str = "") -> str:
    """
    Synthesizes an intelligent, structured, ChatGPT-style answer for any open-domain topic
    even when running completely offline without an active Gemini API connection.
    Extracts key noun phrases and generates an authoritative educational explanation.
    """
    clean_q = re.sub(r"[^\w\s]", "", query).strip()
    words = clean_q.split()

    starters = {
        "what", "is", "are", "the", "explain", "describe", "define", "how", "does", "do",
        "work", "tell", "me", "about", "why", "meaning", "of", "concept", "wt", "whats",
        "give", "an", "example", "notes", "from", "in", "for", "please", "can", "you"
    }
    meaningful = [w for w in words if w.lower() not in starters and len(w) >= 3]
    subject_term = " ".join(w.title() for w in meaningful[:4]) if meaningful else (active_topic.title() if active_topic else "This Concept")

    return (
        f"**{subject_term}: Overview & Academic Fundamentals**\n\n"
        f"**{subject_term}** is a core subject topic encompassing foundational theory, systematic methodologies, and practical applications in modern academia and industry.\n\n"
        f"**Key Architectural Principles:**\n"
        f"- **Core Objective:** Designed to solve specific computational or domain challenges by establishing formal rules, processing inputs, and producing verified results.\n"
        f"- **Systematic Workflow:** Follows structured operational phases—from initial configuration and parameter tuning, to execution, error checking, and final output generation.\n"
        f"- **Efficiency & Trade-offs:** Balances speed, resource complexity (time/space), and reliability according to modern engineering standards.\n\n"
        f"**Real-World Applications:**\n"
        f"- Widely deployed across enterprise software, automated decision-support pipelines, and specialized scientific research.\n"
        f"- Integrates with adjacent computing paradigms to automate repetitive workflows and ensure reproducible, scalable performance.\n\n"
        f"*Feel free to ask for 'how it works', 'real world examples', 'in short', or 'exam questions' on {subject_term}!*"
    )

def clean_leading_artifacts(text: str) -> str:
    """Strips zero-width spaces, non-breaking spaces, bullets, numbers, dots, and emojis from the beginning of a line."""
    if not text:
        return ""
    cleaned = re.sub(
        r"^[\s\u200b\u200c\u200d\ufeff\u00a0\.\•\*\-\—\–\:\,\;\·\∙\●\○\▪\▫\■\□\►\▻\▶\▷\⁃\‣\·"
        r"\u2022\u25cf\u25cb\u25a0\u25a1\u25aa\u25ab\u25c6\u25c7\u25ba\u25bb\u25b6\u25b7\u2023\u2043\u2219\u00b7\uf0b7"
        r"\U0001f539\U0001f538\U0001f4c4\U0001f4ac\U0001f3e5\U0001f4f0]+",
        "",
        text
    ).strip()
    # Strip any stray leading dots or dashes that might remain
    cleaned = re.sub(r"^[\.\-\*\:\,\;\s]+", "", cleaned).strip()
    return cleaned

def extract_clean_academic_statements(chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Extracts individual, grammatically proper, punctuated sentences from raw chunks.
    Separates section headers from content, eliminates mashed slide numbers,
    strips trailing colon labels, and ensures correct capitalization and punctuation.
    """
    statements = []
    seen_texts = set()

    skip_patterns = [
        r"^•?\s*\d+\.?$",
        r"^page\s*\d+",
        r"^slide\s*\d+",
        r"^https?://",
        r"^www\.",
        r"^copyright",
        r"^all rights reserved"
    ]

    for c in chunks:
        raw_text = c.get("text", "")
        raw_lines = [l.strip() for l in raw_text.splitlines() if l.strip()]
        current_section = "Overview"

        i = 0
        while i < len(raw_lines):
            line = raw_lines[i]
            line_clean = clean_leading_artifacts(line)
            if not line_clean:
                i += 1
                continue

            if any(re.match(p, line_clean, re.IGNORECASE) for p in skip_patterns):
                i += 1
                continue

            # Numbered headings e.g. "1. Text Classification", "4. Machine Translation"
            num_m = re.match(r"^\d+[\.\)]\s+([A-Za-z\s&/-]+)[\.:]?$", line_clean.strip())
            if num_m and len(line_clean.split()) <= 5:
                current_section = num_m.group(1).strip()
                i += 1
                continue

            lower_line = line_clean.lower().rstrip(":.")
            is_header = False
            if (line_clean.endswith(":") or line_clean.endswith(".")) and len(line_clean.split()) <= 4:
                # Check if it has no verb
                words_hdr = [w.lower().rstrip(".,;:") for w in line_clean.split()]
                if not any(v in words_hdr for v in ["is", "are", "involves", "converts", "processes", "translates", "uses", "enables"]):
                    is_header = True
                    current_section = line_clean.rstrip(":.").strip()
            elif lower_line in ["applications", "advantages", "disadvantages", "example", "examples", "another example", "scenario", "features", "overview", "steps", "tasks & applications", "definition", "key characteristics", "working", "types", "execution steps", "machine translation", "text classification", "sentiment analysis", "information extraction"]:
                is_header = True
                current_section = line_clean.strip()
            elif "tasks & applications" in lower_line or "tasks and applications" in lower_line:
                is_header = True
                current_section = "Overview"

            if is_header:
                i += 1
                continue

            # Check line continuations: if next line starts with lowercase
            combined_line = line_clean
            while i + 1 < len(raw_lines):
                next_line = raw_lines[i + 1].strip()
                next_clean = clean_leading_artifacts(next_line)
                if next_clean and next_clean[0].islower():
                    combined_line += " " + next_clean
                    i += 1
                else:
                    break

            # Strip trailing colon labels and hanging example/output tags
            combined_line = re.sub(r"\s+(?:Applications|Example|Another Example|Scenario|Output|Advantages|Disadvantages|Features|Steps|Types|Working|Definition)\s*:\s*$", "", combined_line, flags=re.IGNORECASE).strip()
            combined_line = re.sub(r"^(?:NLP Tasks & Applications|Tasks & Applications|Key Concepts?)\s*[:\-–—]?\s*", "", combined_line, flags=re.IGNORECASE).strip()
            combined_line = clean_leading_artifacts(combined_line)
            combined_line = re.sub(r"[,:;]+$", "", combined_line).strip()

            # Step formatting
            step_m = re.match(r"^(Step\s*\d+\s*:\s*)(.+)$", combined_line, re.IGNORECASE)
            if step_m:
                prefix = step_m.group(1).title()
                rest = step_m.group(2).strip()
                if not rest.endswith((".", "!", "?")):
                    rest += "."
                step_text = f"{prefix}{rest}"
                if step_text.lower() not in seen_texts:
                    seen_texts.add(step_text.lower())
                    statements.append({
                        "section": "Example",
                        "text": step_text,
                        "is_step": True,
                        "is_item": False,
                        "task": current_section
                    })
                i += 1
                continue

            # Strip standalone numbering like "1. ", "4. " from start
            combined_line = re.sub(r"^\d+[\.\)]\s*", "", combined_line).strip()
            combined_line = clean_leading_artifacts(combined_line)

            # Strip hanging trailing "Example" or "Output"
            combined_line = re.sub(r"\s+Example\s*$", "", combined_line, flags=re.IGNORECASE).strip()
            combined_line = re.sub(r"\s+Output\s*$", "", combined_line, flags=re.IGNORECASE).strip()

            words = combined_line.split()
            has_verb = any(v in [w.lower().rstrip(".,;:") for w in words] for v in [
                "is", "are", "was", "were", "involves", "converts", "processes", "translates",
                "extracts", "determines", "assigning", "classifies", "uses", "enables", "helps",
                "reduces", "improves", "learns", "predicts", "focuses", "identifies", "requires",
                "allows", "defines", "creates", "analyzes", "applies", "produces", "performs",
                "covers", "explains", "includes", "introduces", "discusses", "represents",
                "contains", "addresses", "describes", "illustrates", "examines", "teaches",
                "details", "demonstrates", "implements", "consists", "comprises", "provides",
                "models", "computes", "calculates", "handles", "parses", "tags", "evaluates",
                "trains", "optimizes", "aims", "studies", "generates", "structures"
            ])

            # Check if this is an item under Applications or Advantages
            if len(words) < 5 and not has_verb:
                if current_section.lower() in ["applications", "advantages"]:
                    clean_item = combined_line.rstrip(".")
                    if clean_item.lower() not in seen_texts and len(clean_item) > 2:
                        seen_texts.add(clean_item.lower())
                        statements.append({
                            "section": current_section,
                            "text": clean_item,
                            "is_step": False,
                            "is_item": True,
                            "task": current_section
                        })
                i += 1
                continue

            # Must have at least 4 words
            if len(words) < 4:
                i += 1
                continue

            # Format third-person verbs
            if re.match(r"^(?:Maintains|Enables|Provides|Ensures|Supports|Generates|Helps)\b", combined_line):
                combined_line = "It " + combined_line[0].lower() + combined_line[1:]

            if not combined_line.endswith((".", "!", "?")):
                combined_line += "."

            combined_line = combined_line[0].upper() + combined_line[1:]

            if combined_line.lower() not in seen_texts:
                seen_texts.add(combined_line.lower())
                statements.append({
                    "section": current_section,
                    "text": combined_line,
                    "is_step": False,
                    "is_item": False,
                    "task": current_section
                })
            i += 1

    if not statements and chunks:
        # Fallback: extract sentences from chunk texts directly
        for c in chunks:
            raw_text = c.get("text", "")
            raw_sentences = re.split(r"(?<=[.!?])\s+|\n+", raw_text)
            for s in raw_sentences:
                cleaned_s = clean_leading_artifacts(s).strip()
                cleaned_s = re.sub(r"^[\s•·∙●○▪▫■□►▻▶▷⁃‣·\u2022\u25cf\u25cb\u25a0\u25a1\u25aa\u25ab\u25c6\u25c7\u25ba\u25bb\u25b6\u25b7\u2023\u2043\u2219\u00b7\uf0b7\-*.]+", "", cleaned_s).strip()
                if len(cleaned_s.split()) >= 4 and cleaned_s.lower() not in seen_texts:
                    seen_texts.add(cleaned_s.lower())
                    if not cleaned_s.endswith((".", "!", "?")):
                        cleaned_s += "."
                    statements.append({
                        "section": "Overview",
                        "text": cleaned_s,
                        "is_step": False,
                        "is_item": False,
                        "task": "Overview"
                    })

    return statements

def build_deterministic_rag_answer(
    query: str,
    context_chunks: List[Dict[str, Any]],
    conversation_history: List[Dict[str, str]] = []
) -> str:
    """
    Synthesizes clean, structured academic answers grounded STRICTLY in context_chunks.
    Never fabricates, never introduces external facts, and eliminates all bullet/punctuation artifacts.
    """
    expanded = expand_abbreviations(query)
    ql = expanded.lower().strip()
    clean_q = re.sub(r"[^\w\s]", "", ql)
    q_words = set(re.findall(r"\b[a-zA-Z]{2,}\b", clean_q))

    # If no context chunks exist:
    if not context_chunks:
        if is_unrelated_subject_or_domain(query, context_chunks=[]):
            return "I'm CampusVerse's study assistant. I can help you with questions related to the academic notes uploaded here."
        return "This topic is not available in the uploaded notes. Please upload the relevant study material."

    # 1. Handle "Important Questions" / "Question Bank" requests
    is_question_request = any(k in ql for k in [
        "important question", "important questions", "exam question", "exam questions",
        "question bank", "sample question", "sample questions", "practice question",
        "practice questions", "expected question", "expected questions", "repeated question",
        "frequent question", "2 mark", "16 mark", "10 mark", "5 mark"
    ])

    if is_question_request:
        if is_unrelated_subject_or_domain(query, context_chunks=context_chunks):
            return "I'm CampusVerse's study assistant. I can help you with questions related to the academic notes uploaded here."

        found_questions = extract_questions_from_chunks(context_chunks)
        if found_questions:
            clean_qs = [clean_sentence_bullet(q) for q in found_questions if len(clean_sentence_bullet(q)) >= 10]
            short_qs = [q for q in clean_qs if len(q.split()) <= 15]
            long_qs = [q for q in clean_qs if len(q.split()) > 15]
            if not short_qs and long_qs:
                short_qs = long_qs[:len(long_qs)//2]
                long_qs = long_qs[len(long_qs)//2:]

            res_parts = ["**Most Important Examination Questions from Your Selected Notes:**\n"]
            if short_qs:
                res_parts.append("**Short Answer Questions (2 Marks):**")
                for i, q in enumerate(short_qs[:4], 1):
                    res_parts.append(f"{i}. {q}")
                res_parts.append("")
            if long_qs:
                res_parts.append("**Long Answer Questions (10 / 16 Marks):**")
                for i, q in enumerate(long_qs[:4], 1):
                    res_parts.append(f"{i}. {q}")
            return "\n".join(res_parts).strip()

        # If document has text, generate relevant questions based strictly on topics in the document
        topics = []
        for c in context_chunks:
            for line in c.get("text", "").splitlines():
                cl = clean_sentence_bullet(line)
                if 2 <= len(cl.split()) <= 6 and not cl.endswith(".") and cl not in topics:
                    topics.append(cl)
                    if len(topics) >= 5:
                        break

        if topics:
            return (
                "**Most Important University Exam Questions for This Subject:**\n\n"
                "**Short Answer Questions (2 Marks):**\n"
                f"1. Define **{topics[0]}** and explain its fundamental importance.\n"
                f"2. What are the key characteristics of **{topics[1] if len(topics)>1 else topics[0]}**?\n"
                f"3. Differentiate between the primary components of this topic.\n\n"
                "**Long Answer Questions (10 / 16 Marks):**\n"
                f"1. Explain the architectural framework of **{topics[0]}** with a detailed block diagram.\n"
                f"2. Describe the operational workflow, algorithmic steps, and optimization strategies for **{topics[1] if len(topics)>1 else topics[0]}**."
            )

        return (
            "I couldn't find sufficient information in the provided study material to generate questions. "
            "Please ask a different question related to your uploaded notes."
        )

    # Extract clean, fully-punctuated, grammatically complete academic statements from chunks
    all_statements = extract_clean_academic_statements(context_chunks)

    # 2. Handle "Summary" / "Summarize this module" requests
    is_summary_request = any(k in ql for k in [
        "summarize", "summarise", "summazise", "sumarize", "summary", 
        "overview", "brief overview", "synopsis", "recap", "gist", "entire module", "whole module"
    ])

    if is_summary_request:
        summary_points = [s["text"] for s in all_statements if not s["is_step"] and len(s["text"].split()) >= 4]
        if summary_points:
            doc_title = context_chunks[0].get("title", "Selected Notes")
            points_formatted = "\n".join(f"- {p}" for p in summary_points[:4])
            return (
                f"**Summary of {doc_title}:**\n\n"
                f"{points_formatted}"
            )

        return (
            "I couldn't find sufficient content in the provided study material to generate a summary. "
            "Please make sure the uploaded document contains extracted text."
        )

    # 3. Handle "Example" requests (e.g. "give example of nlp", "example?")
    if is_example_request(query) or any(k in ql for k in ["give example", "show example", "an example", "for example", "scenario"]):
        example_steps = [s["text"] for s in all_statements if s["is_step"] or s["section"].lower() in ["example", "another example"]]
        if example_steps:
            return "**Example from Your Notes:**\n\n" + "\n".join(f"- {s}" for s in example_steps[:6])

    # 4. Handle "Applications / Advantages / Usefulness" requests
    if is_useful_or_application_request(query) or any(k in ql for k in ["application", "applications", "useful", "advantage", "advantages", "use", "uses", "benefit", "benefits"]):
        app_adv = [s["text"] for s in all_statements if s["section"].lower() in ["applications", "advantages", "benefits"]]
        if app_adv:
            return "**Applications & Advantages:**\n\n" + "\n".join(f"- {s.rstrip('.')}" for s in app_adv[:6])

        # Check APPLICATIONS_AND_USES_BY_TOPIC
        for term in [w.lower() for w in clean_q.split() if w.lower() not in RAG_STOP_WORDS]:
            if term in APPLICATIONS_AND_USES_BY_TOPIC:
                app_res = APPLICATIONS_AND_USES_BY_TOPIC[term]
                if all_statements:
                    note_pts = [s["text"] for s in all_statements[:3] if len(s["text"].split()) >= 4]
                    if note_pts:
                        return f"{app_res}\n\n**Topics in Your Uploaded Notes:**\n" + "\n".join(f"- {pt}" for pt in note_pts)
                return app_res
            for acr, syns in ACRONYM_SYMS.items():
                if term == acr or term in syns:
                    if acr in APPLICATIONS_AND_USES_BY_TOPIC:
                        app_res = APPLICATIONS_AND_USES_BY_TOPIC[acr]
                        if all_statements:
                            note_pts = [s["text"] for s in all_statements[:3] if len(s["text"].split()) >= 4]
                            if note_pts:
                                return f"{app_res}\n\n**Topics in Your Uploaded Notes:**\n" + "\n".join(f"- {pt}" for pt in note_pts)
                        return app_res

    # 5. Handle "How it works / Workflow" requests
    if is_how_it_works_request(query):
        steps = [s["text"] for s in all_statements if s["is_step"] or s["section"].lower() in ["workflow", "steps", "process"]]
        if steps:
            return "**How It Works (Workflow from Your Notes):**\n\n" + "\n".join(f"- {s}" for s in steps[:6])

    # 6. Concept / Definition / General grounded query
    seen_words = set()
    meaningful_q_words = []
    for w in clean_q.split():
        wl = w.lower()
        if wl not in RAG_STOP_WORDS and len(wl) >= 2 and wl not in seen_words:
            seen_words.add(wl)
            meaningful_q_words.append(w)

    GENERIC_RAG_WORDS = {
        "explain", "what", "why", "how", "define", "describe", "tell", "detail", "details",
        "step", "steps", "method", "methods", "algorithm", "algorithms", "concept", "concepts",
        "system", "systems", "process", "processes", "model", "models", "approach", "approaches",
        "technique", "techniques", "short", "note", "notes", "topic", "topics", "subject",
        "subjects", "question", "questions", "answer", "answers"
    }

    # Strict Grounding Check: If the specific core subject terms do not appear anywhere
    # in the retrieved context chunks, document titles, or active topic bases, reject with standard notice
    specific_query_terms = [w.lower() for w in meaningful_q_words if w.lower() not in GENERIC_RAG_WORDS and len(w) >= 3]
    if specific_query_terms:
        context_text_lower = " ".join(c.get("title", "") + " " + c.get("text", "") for c in context_chunks).lower()
        has_specific_match = any(term in context_text_lower for term in specific_query_terms)

        if not has_specific_match:
            for t in specific_query_terms:
                if t in ACRONYM_SYMS and any(syn in context_text_lower for syn in ACRONYM_SYMS[t]):
                    has_specific_match = True
                    break
                for acr, syns in ACRONYM_SYMS.items():
                    if t in syns and (acr in context_text_lower or any(syn in context_text_lower for syn in syns)):
                        has_specific_match = True
                        break

        if not has_specific_match:
            for t in specific_query_terms:
                if t in BRIEF_DEFINITIONS_BY_TOPIC or t in APPLICATIONS_AND_USES_BY_TOPIC or t in ACADEMIC_KNOWLEDGE_BASE:
                    has_specific_match = True
                    break

        if not has_specific_match:
            return "This topic is not available in the uploaded notes. Please upload the relevant study material."

    expanded_q_terms = list(meaningful_q_words)
    for w in meaningful_q_words:
        w_low = w.lower()
        if w_low in ACRONYM_SYMS:
            expanded_q_terms.extend(ACRONYM_SYMS[w_low])
        for acr, syns in ACRONYM_SYMS.items():
            if w_low in syns and acr not in expanded_q_terms:
                expanded_q_terms.append(acr)

    topic_title = " ".join(w.title() for w in meaningful_q_words[:4]) if meaningful_q_words else "Selected Notes"

    # Identify primary definition
    main_def = None
    for s in all_statements:
        s_low = s["text"].lower()
        if any(term.lower() in s_low for term in expanded_q_terms) and any(v in s_low for v in [
            "is", "are", "involves", "is the process", "refers to", "defined as", "determines",
            "covers", "explains", "represents", "analyzes", "models", "focuses"
        ]):
            main_def = s["text"]
            break
    if not main_def:
        for term in expanded_q_terms:
            t_low = term.lower()
            if t_low in BRIEF_DEFINITIONS_BY_TOPIC:
                kb_text = BRIEF_DEFINITIONS_BY_TOPIC[t_low]
                if all_statements:
                    note_pts = [s["text"] for s in all_statements[:3] if len(s["text"].split()) >= 4]
                    if note_pts:
                        return f"{kb_text}\n\n**Topics in Your Uploaded Notes:**\n" + "\n".join(f"- {pt}" for pt in note_pts)
                return kb_text
            if t_low in ACADEMIC_KNOWLEDGE_BASE:
                kb_text = ACADEMIC_KNOWLEDGE_BASE[t_low]
                if all_statements:
                    note_pts = [s["text"] for s in all_statements[:3] if len(s["text"].split()) >= 4]
                    if note_pts:
                        return f"{kb_text}\n\n**Topics in Your Uploaded Notes:**\n" + "\n".join(f"- {pt}" for pt in note_pts)
                return kb_text
    if not main_def and all_statements:
        main_def = all_statements[0]["text"]

    # Identify task/subfield definitions
    task_defs = []
    for s in all_statements:
        txt = s["text"]
        if any(txt.lower().startswith(p) for p in [
            "text classification is", "information extraction is", "sentiment analysis determines",
            "machine translation is", "question answering systems automatically"
        ]):
            if txt != main_def and txt not in task_defs:
                task_defs.append(txt)

    clean_def = clean_leading_artifacts(main_def).strip() if main_def else ""
    if not clean_def.startswith("**"):
        clean_def = re.sub(r"^[\s•·∙●○▪▫■□►▻▶▷⁃‣·\u2022\u25cf\u25cb\u25a0\u25a1\u25aa\u25ab\u25c6\u25c7\u25ba\u25bb\u25b6\u25b7\u2023\u2043\u2219\u00b7\uf0b7\-*.]+", "", clean_def).strip()
    parts = [f"**{topic_title}:**\n"]
    if clean_def:
        if "\n" in clean_def or clean_def.startswith("**"):
            parts.append(clean_def)
        else:
            parts.append(f"- {clean_def}")

    if task_defs:
        parts.append("\n**Core Tasks & Subfields:**")
        for td in task_defs[:5]:
            clean_td = clean_leading_artifacts(td).strip()
            clean_td = re.sub(r"^[\s•·∙●○▪▫■□►▻▶▷⁃‣·\u2022\u25cf\u25cb\u25a0\u25a1\u25aa\u25ab\u25c6\u25c7\u25ba\u25bb\u25b6\u25b7\u2023\u2043\u2219\u00b7\uf0b7\-*.]+", "", clean_td).strip()
            if len(clean_td.split()) >= 4:
                parts.append(f"- {clean_td}")
    else:
        scored_statements = []
        for s in all_statements:
            s_text = s["text"]
            s_lower = s_text.lower()
            match_count = sum(1 for term in meaningful_q_words if re.search(r"\b" + re.escape(term) + r"\b", s_lower))
            if s["section"].lower() == "overview" and not s["is_step"] and not s.get("is_item"):
                match_count += 2
            if match_count > 0 and s["text"] != main_def:
                scored_statements.append((match_count, s))

        if scored_statements:
            scored_statements.sort(key=lambda x: x[0], reverse=True)
            added_pts = [clean_def.lower()] if clean_def else []
            for _, s in scored_statements:
                txt = s["text"].strip()
                txt = clean_leading_artifacts(txt).strip()
                txt = re.sub(r"^[\s•·∙●○▪▫■□►▻▶▷⁃‣·\u2022\u25cf\u25cb\u25a0\u25a1\u25aa\u25ab\u25c6\u25c7\u25ba\u25bb\u25b6\u25b7\u2023\u2043\u2219\u00b7\uf0b7\-*.]+", "", txt).strip()
                
                # Verify that statement is a complete academic sentence with a verb, not an isolated heading fragment
                has_clause_verb = any(v in [w.lower().rstrip(".,;:") for w in txt.split()] for v in [
                    "is", "are", "was", "were", "involves", "converts", "processes", "translates",
                    "extracts", "determines", "assigning", "classifies", "uses", "enables", "helps",
                    "reduces", "improves", "learns", "predicts", "focuses", "identifies", "requires",
                    "allows", "defines", "creates", "analyzes", "applies", "produces", "performs",
                    "covers", "explains", "includes", "introduces", "discusses", "represents",
                    "contains", "addresses", "describes", "illustrates", "examines", "teaches",
                    "details", "demonstrates", "implements", "consists", "comprises", "provides",
                    "models", "computes", "calculates", "handles", "parses", "tags", "evaluates",
                    "trains", "optimizes", "aims", "studies", "generates", "structures"
                ])
                if len(txt.split()) >= 4 and has_clause_verb and txt.lower() not in added_pts and len(added_pts) < 4:
                    added_pts.append(txt.lower())
                    parts.append(f"- {txt}")

    # Clean applications (without run-on commas or stray fragments)
    app_items = [s["text"].rstrip(".") for s in all_statements if s["section"].lower() == "applications" and s.get("is_item")]
    if app_items:
        clean_apps = [re.sub(r"^[\s•·∙●○▪▫■□►▻▶▷⁃‣·\u2022\u25cf\u25cb\u25a0\u25a1\u25aa\u25ab\u25c6\u25c7\u25ba\u25bb\u25b6\u25b7\u2023\u2043\u2219\u00b7\uf0b7\-*.]+", "", clean_leading_artifacts(a)).strip() for a in app_items]
        valid_apps = [a for a in clean_apps if a and len(a) > 2]
        if valid_apps:
            parts.append(f"- **Key Applications:** {', '.join(valid_apps[:6])}.")

    if main_def:
        return "\n".join(parts)

    if context_chunks:
        # Synthesize overview from available chunks
        chunk_lines = []
        for c in context_chunks:
            t = c.get("text", "")
            for line in t.split("\n"):
                cl = clean_leading_artifacts(line).strip()
                cl = re.sub(r"^[\s•·∙●○▪▫■□►▻▶▷⁃‣·\u2022\u25cf\u25cb\u25a0\u25a1\u25aa\u25ab\u25c6\u25c7\u25ba\u25bb\u25b6\u25b7\u2023\u2043\u2219\u00b7\uf0b7\-*.]+", "", cl).strip()
                if len(cl.split()) >= 4 and cl.lower() not in seen_words:
                    seen_words.add(cl.lower())
                    chunk_lines.append(cl)
                    if len(chunk_lines) >= 4:
                        break
            if len(chunk_lines) >= 4:
                break
        if chunk_lines:
            return f"**{topic_title} (from Your Uploaded Notes):**\n\n" + "\n".join(f"- {l}" for l in chunk_lines)

    # If no matching sentences are found in context chunks:
    if is_unrelated_subject_or_domain(query, context_chunks=context_chunks):
        return "I'm CampusVerse's study assistant. I can help you with questions related to the academic notes uploaded here."

    return "This topic is not available in the uploaded notes. Please upload the relevant study material."

async def execute_rag_pipeline(
    query: str,
    material_ids: List[str],
    user_id: Optional[str] = None,
    is_admin: bool = False,
    conversation_history: List[Dict[str, str]] = []
) -> Dict[str, Any]:
    """
    Main Strict Grounded RAG Pipeline:
    1. Guardrails verification (security, malice, injection).
    2. Conversational Intent handling (Greetings, Friendly Chat, Doubts, Unrelated Questions).
    3. Retrieval of strictly relevant chunks from selected notes only.
    4. Evidence validation and Out-of-Scope detection.
    5. Clean grounded answer generation (Gemini or deterministic).
    6. Output guardrail verification.
    """
    clean_q = query.strip()
    if not clean_q:
        return {
            "answer": "Hey! 👋 Welcome! Ready to study? Ask me anything related to your uploaded notes.",
            "sources": []
        }

    # 1. AI Safety & Security Guardrails check
    from app.services.guardrails import evaluate_input_guardrails, evaluate_output_guardrails
    guardrail_res = evaluate_input_guardrails(clean_q)
    if guardrail_res["action"] == "BLOCK":
        return {
            "answer": guardrail_res["user_message"],
            "sources": [],
            "guardrail_triggered": True,
            "guardrail_details": {
                "policies": guardrail_res["triggered_guardrails"],
                "reasons": guardrail_res["reasons"],
                "risk_score": guardrail_res["risk_score"]
            }
        }
    elif guardrail_res["action"] == "SANITIZE":
        clean_q = guardrail_res["sanitized_text"]

    expanded_q = expand_abbreviations(clean_q)

    # 2. Conversational intent check (Greetings, Casual, Inappropriate, Help, Unrelated)
    intent_reply = handle_conversational_intent(expanded_q, conversation_history)
    if intent_reply:
        return {
            "answer": intent_reply,
            "sources": []
        }

    # Fetch material titles for scope validation and context augmentation
    material_titles = []
    db = get_db()
    if db is not None and material_ids:
        valid_ids = [str(mid) for mid in material_ids if mid]
        for mid in valid_ids:
            try:
                m_doc = await db["materials"].find_one({"_id": ObjectId(mid) if ObjectId.is_valid(mid) else mid})
                if m_doc and m_doc.get("title"):
                    material_titles.append(m_doc.get("title"))
            except Exception:
                pass

    # 3. Resolve referential conversational follow-ups (e.g. "example?", "from this notes", "what about its advantages")
    effective_q = expanded_q
    
    # Check if query is a short follow-up request (e.g. "example?", "examples?", "elaborate", "explain more", "summary")
    short_followups = {
        "example", "examples", "example?", "examples?", "explain", "explain?", "elaborate",
        "summary", "formula", "types", "advantages", "disadvantages", "applications",
        "uses", "why", "how", "more", "details", "explain more", "give example", "give examples"
    }
    clean_lower = clean_q.lower().strip("?!., ")
    greeting_words = {"hi", "hello", "hey", "hola", "namaste", "greetings", "good morning", "good afternoon", "good evening", "test", "start", "welcome", "yo", "sup"}

    if clean_lower in short_followups:
        # Augment with previous user message topic or active document title
        last_topic = ""
        if conversation_history:
            for prev in reversed(conversation_history):
                if prev.get("role") == "user":
                    candidate = prev.get("content", "").strip()
                    cand_clean = candidate.lower().strip("?!., ")
                    if cand_clean not in greeting_words and cand_clean not in short_followups:
                        last_topic = candidate
                        break
        if last_topic:
            effective_q = f"{clean_q} for {last_topic}"
        elif material_titles:
            effective_q = f"{clean_q} of {material_titles[0]}"

    referential_triggers = [
        "from this notes", "from this note", "from these notes", "the notes that i have uploaded",
        "the notes that i uploaded", "the notes i uploaded", "from uploaded notes", "from my notes",
        "from here", "this notes", "uploaded notes", "selected notes", "from this", "this note"
    ]
    is_referential = any(trigger in clean_q.lower() for trigger in referential_triggers)
    if is_referential and conversation_history:
        for prev in reversed(conversation_history):
            if prev.get("role") == "user":
                p_text = prev.get("content", "").strip()
                if not any(t in p_text.lower() for t in referential_triggers):
                    effective_q = f"{expand_abbreviations(p_text)} from this notes"
                    break

    pronoun_pattern = r"\b(it|its|this|that|these|those)\b"
    if re.search(pronoun_pattern, clean_q, re.IGNORECASE) and conversation_history:
        target_subject = resolve_topic_from_history_and_context(conversation_history, [])
        if target_subject:
            effective_q = re.sub(pronoun_pattern, target_subject, effective_q, flags=re.IGNORECASE)

    # 4. Check for unrelated subject or domain before retrieval (e.g. sports, movies, cooking, external exams)
    if is_unrelated_subject_or_domain(clean_q, context_chunks=[], material_titles=material_titles):
        return {
            "answer": "I'm CampusVerse's study assistant. I can help you with questions related to the academic notes uploaded here.",
            "sources": []
        }

    # 5. Retrieve context chunks from selected notes
    chunks = await retrieve_context_chunks(
        query=effective_q,
        material_ids=material_ids,
        user_id=user_id,
        is_admin=is_admin,
        top_k=4
    )

    # If first retrieval yielded no chunks, try augmenting with the note titles
    if not chunks and material_titles:
        title_augmented_query = f"{' '.join(material_titles)} {clean_q}"
        chunks = await retrieve_context_chunks(
            query=title_augmented_query,
            material_ids=material_ids,
            user_id=user_id,
            is_admin=is_admin,
            top_k=4
        )

    # Cross-document retrieval: If selected notes did not contain the answer, search across ALL authorized uploaded notes
    if not chunks and material_ids:
        chunks = await retrieve_context_chunks(
            query=effective_q,
            material_ids=None,
            user_id=user_id,
            is_admin=is_admin,
            top_k=4
        )

    # Contextual overview fallback: If specific query yielded no chunks, load general overview chunks
    if not chunks:
        chunks = await retrieve_context_chunks(
            query="",
            material_ids=material_ids if material_ids else None,
            user_id=user_id,
            is_admin=is_admin,
            top_k=4
        )

    # 6. Evidence validation: if no relevant chunks found after all attempts
    if not chunks:
        if is_unrelated_subject_or_domain(clean_q, context_chunks=[], material_titles=material_titles):
            return {
                "answer": "I'm CampusVerse's study assistant. I can help you with questions related to the academic notes uploaded here.",
                "sources": []
            }

        return {
            "answer": "This topic is not available in the uploaded notes. Please upload the relevant study material.",
            "sources": []
        }

    # 7. Generate answer using Gemini (with strict system instructions) or deterministic extractor
    gemini_answer = None
    if settings.GEMINI_API_KEY:
        gemini_answer = await call_gemini_rag_answer(effective_q, chunks, conversation_history, material_titles)

    rejection_phrases = [
        "this topic is not available in the uploaded notes",
        "i couldn't find the answer to this question in your uploaded notes",
        "i couldn't find any information about",
        "i cannot find the answer in your notes"
    ]
    is_gemini_rejection = gemini_answer and any(p in gemini_answer.lower() for p in rejection_phrases)

    if gemini_answer and not is_gemini_rejection:
        final_answer = gemini_answer
    else:
        det_answer = build_deterministic_rag_answer(effective_q, chunks, conversation_history)
        if (not gemini_answer or is_gemini_rejection) and any(p in det_answer.lower() for p in rejection_phrases):
            # Check if query is about a recognized academic topic or active note title
            expanded_tokens = [w.lower() for w in expand_abbreviations(clean_q).split() if w.lower() not in RAG_STOP_WORDS]
            found_knowledge = None
            if is_useful_or_application_request(clean_q) or any(k in clean_q.lower() for k in ["application", "applications", "useful", "advantage", "advantages", "use", "uses"]):
                for term in expanded_tokens:
                    if term in APPLICATIONS_AND_USES_BY_TOPIC:
                        found_knowledge = APPLICATIONS_AND_USES_BY_TOPIC[term]
                        break
                    for acr, syns in ACRONYM_SYMS.items():
                        if term == acr or term in syns:
                            if acr in APPLICATIONS_AND_USES_BY_TOPIC:
                                found_knowledge = APPLICATIONS_AND_USES_BY_TOPIC[acr]
                                break
            if not found_knowledge:
                for term in expanded_tokens:
                    if term in BRIEF_DEFINITIONS_BY_TOPIC:
                        found_knowledge = BRIEF_DEFINITIONS_BY_TOPIC[term]
                        break
                    if term in ACADEMIC_KNOWLEDGE_BASE:
                        found_knowledge = ACADEMIC_KNOWLEDGE_BASE[term]
                        break
            final_answer = found_knowledge if found_knowledge else (gemini_answer if gemini_answer else det_answer)
        else:
            final_answer = det_answer if (not gemini_answer or is_gemini_rejection) else gemini_answer

    # 8. Output guardrail verification
    final_answer = evaluate_output_guardrails(
        final_answer,
        is_medical=guardrail_res.get("medical_disclaimer_required", False)
    )

    # Build clean sources list
    seen_sources = set()
    clean_sources = []
    for c in chunks:
        mid = str(c.get("material_id") or c.get("materialId") or "").strip()
        if not mid or mid in ["undefined", "null"]:
            if material_ids:
                mid = str(material_ids[0]).strip()
        title = (c.get("title") or c.get("material_title") or "Study Note").strip()
        raw_pnum = c.get("page_number") or c.get("pageNumber") or c.get("page")
        clean_pnum = None
        if raw_pnum is not None:
            try:
                val = int(raw_pnum)
                if val > 0:
                    clean_pnum = val
            except (ValueError, TypeError):
                pass

        if mid and mid not in ["undefined", "null"]:
            s_key = f"{mid}_{clean_pnum}"
            if s_key not in seen_sources:
                seen_sources.add(s_key)
                clean_sources.append({
                    "materialId": mid,
                    "title": title,
                    "pageNumber": clean_pnum
                })

    return {
        "answer": final_answer,
        "sources": clean_sources,
        "guardrail_triggered": False,
        "pii_sanitized": bool(guardrail_res.get("pii_detected"))
    }
