package main

import (
	"bytes"
	"context"
	"fmt"
	"io"
	"net/http"

	"cloud.google.com/go/storage"
	"github.com/GoogleCloudPlatform/functions-framework-go/functions"
)

func init() {
	functions.HTTP("upload", uploadHandler)
}

// https://us-central1-ankur-personal.cloudfunctions.net/upload
func uploadHandler(w http.ResponseWriter, r *http.Request) {
	// Parse the multipart form data
	err := r.ParseMultipartForm(32 << 20) // 32MB
	if err != nil {
		http.Error(w, "Failed to parse multipart form data", http.StatusBadRequest)
		return
	}

	// Get the uploaded files
	files := r.MultipartForm.File["files"]

	// Iterate over the uploaded files
	for _, file := range files {
		// Open the uploaded file
		f, err := file.Open()
		if err != nil {
			http.Error(w, "Failed to open uploaded file", http.StatusInternalServerError)
			return
		}
		defer f.Close()

		// Read the file content
		content, err := io.ReadAll(f)

		// Upload the file content to GCS
		err = uploadToGCS(file.Filename, content)
		if err != nil {
			http.Error(w, "Failed to upload file to GCS", http.StatusInternalServerError)
			return
		}

		// Print the file name and size
		fmt.Printf("File Name: %s, Size: %d bytes\n", file.Filename, len(content))
		fmt.Fprintf(w, "File Name: %s, Size: %d bytes\n", file.Filename, len(content))
	}

	// Send a success response
	w.WriteHeader(http.StatusOK)
	fmt.Fprint(w, "Files uploaded successfully")
}

func uploadToGCS(filename string, content []byte) error {
	// Set up your Google Cloud Storage client
	ctx := context.Background()
	client, err := storage.NewClient(ctx)
	if err != nil {
		fmt.Println(err)
		return fmt.Errorf("failed to create client: %v", err)
	}
	defer client.Close()

	// Create a new bucket handle
	bucket := client.Bucket("ankur_docs")

	// Create a new object handle
	obj := bucket.Object(filename)

	// Create a writer to upload the file content
	writer := obj.NewWriter(ctx)
	defer writer.Close()

	// Write the file content to the object
	_, err = io.Copy(writer, bytes.NewReader(content))
	if err != nil {
		return fmt.Errorf("failed to write file content: %v", err)
	}

	return nil
}
