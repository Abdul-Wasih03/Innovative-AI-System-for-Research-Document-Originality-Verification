import React, { useState } from "react";
import { FiUpload } from "react-icons/fi";
import axios from "axios";
import "../styles/Home.css";

const Home = () => {
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState(null);

  const handleFileChange = (e) => {
    setSelectedFile(e.target.files[0]);
  };

  const handleCheckOriginality = async () => {
    if (!selectedFile) {
      alert("Please select a file to upload.");
      return;
    }

    setUploading(true);
    const formData = new FormData();
    formData.append("file", selectedFile);

    try {
      const response = await axios.post("http://localhost:8000/check-similarity/", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });

      setResult(response.data);
      setSelectedFile(null);
    } catch (error) {
      alert("Error checking originality. Please try again.");
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="page-container">
      <div className="content-box">
        <h1>AI-Powered Research Document Originality Checker</h1>
        <p>Upload a document to verify its originality. Our AI will compare it against stored research papers.</p>

        {/* Upload Section */}
        <div className="upload-section">
          <label className="file-upload">
            <FiUpload className="upload-icon" />
            <input type="file" onChange={handleFileChange} accept=".pdf" />
            <span>{selectedFile ? selectedFile.name : "Click to select a file"}</span>
          </label>
          <button onClick={handleCheckOriginality} disabled={uploading} className="upload-btn">
            {uploading ? "Checking..." : "Check Originality"}
          </button>
        </div>

        {/* Match Result Section */}
        {result && (
          <div className="result-section">
            <h2>Plagiarism Check Result</h2>
            <p className="result-text">
              Originality Percentage: <strong>{result.originality.toFixed(2)}%</strong>
            </p>
            <p>Most Similar Document: <strong>{result.most_similar_doc}</strong></p>
            {result.originality < 50 ? (
              <p className="warning">⚠️ High similarity detected! Consider revising your content.</p>
            ) : (
              <p className="safe">✅ Your document is mostly original.</p>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default Home;
