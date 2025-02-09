import React, { useState } from 'react';
import { Camera, Upload } from 'lucide-react';

export default function ScoreUpload() {
  const [score, setScore] = useState('');
  const [preview, setPreview] = useState('');
  const [processing, setProcessing] = useState(false);

  const handleImageUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    setProcessing(true);
    setPreview(URL.createObjectURL(file));

    const formData = new FormData();
    formData.append('image', file);

    try {
      const response = await fetch('/api/process_image', {
        method: 'POST',
        body: formData
      });
      const data = await response.json();
      
      if (data.score) {
        setScore(new Intl.NumberFormat().format(data.score));
      } else {
        throw new Error(data.error || 'Score detection failed');
      }
    } catch (error) {
      alert('Could not detect score. Please try another image.');
    } finally {
      setProcessing(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex gap-2">
        <label className="flex-1">
          <input
            type="file"
            onChange={handleImageUpload}
            accept="image/*"
            capture="environment"
            className="hidden"
          />
          <div className="flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-700 text-white py-2 px-4 rounded cursor-pointer">
            <Camera size={20} />
            <span>Take Photo</span>
          </div>
        </label>
        
        <label className="flex-1">
          <input
            type="file"
            onChange={handleImageUpload}
            accept="image/*"
            className="hidden"
          />
          <div className="flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-700 text-white py-2 px-4 rounded cursor-pointer">
            <Upload size={20} />
            <span>Upload Image</span>
          </div>
        </label>
      </div>

      {preview && (
        <div className="mt-4">
          <img src={preview} className="max-w-full h-auto mx-auto rounded-lg" alt="Score preview" />
          {processing && (
            <div className="text-center mt-2 text-blue-400">
              Processing image...
            </div>
          )}
        </div>
      )}

      <div>
        <label className="block text-center text-xl text-blue-400">SCORE</label>
        <input
          type="text"
          name="score"
          value={score}
          readOnly
          className="w-full bg-indigo-950 border-2 border-blue-500 rounded text-center text-2xl p-2 text-green-400 score-text"
        />
      </div>
    </div>
  );
}