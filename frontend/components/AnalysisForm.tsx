'use client';

import { useState } from 'react';
import { Loader2, Search } from 'lucide-react';

interface AnalysisFormProps {
  onSubmit: (videoUrl: string, maxComments: number) => Promise<void>;
}

export default function AnalysisForm({ onSubmit }: AnalysisFormProps) {
  const [videoUrl, setVideoUrl] = useState('');
  const [maxComments, setMaxComments] = useState(500);
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    try {
      await onSubmit(videoUrl, maxComments);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="bg-white rounded-2xl shadow-xl p-8 max-w-2xl mx-auto">
      <form onSubmit={handleSubmit} className="space-y-6">
        <div>
          <label
            htmlFor="videoUrl"
            className="block text-sm font-medium text-gray-700 mb-2"
          >
            YouTube URL or Video ID
          </label>
          <input
            type="text"
            id="videoUrl"
            value={videoUrl}
            onChange={(e) => setVideoUrl(e.target.value)}
            placeholder="https://www.youtube.com/watch?v=XXXXXXXXXXX"
            className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            required
          />
        </div>

        <div>
          <label
            htmlFor="maxComments"
            className="block text-sm font-medium text-gray-700 mb-2"
          >
            Max Comments: {maxComments}
          </label>
          <input
            type="range"
            id="maxComments"
            min="10"
            max="5000"
            step="10"
            value={maxComments}
            onChange={(e) => setMaxComments(Number(e.target.value))}
            className="w-full"
          />
          <div className="flex justify-between text-xs text-gray-500 mt-1">
            <span>10</span>
            <span>5000</span>
          </div>
        </div>

        <button
          type="submit"
          disabled={isLoading}
          className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white font-semibold py-3 px-6 rounded-lg transition-colors flex items-center justify-center gap-2"
        >
          {isLoading ? (
            <>
              <Loader2 className="w-5 h-5 animate-spin" />
              Starting Analysis...
            </>
          ) : (
            <>
              <Search className="w-5 h-5" />
              Analyze Comments
            </>
          )}
        </button>
      </form>

      <div className="mt-6 p-4 bg-blue-50 rounded-lg">
        <h3 className="font-semibold text-sm text-blue-900 mb-2">Note:</h3>
        <ul className="text-xs text-blue-700 space-y-1">
          <li>• Analysis may take 2-5 minutes depending on comment count</li>
          <li>• Uses OpenAI GPT-4o-mini for sentiment analysis</li>
          <li>• Results are cached for 7 days</li>
        </ul>
      </div>
    </div>
  );
}

