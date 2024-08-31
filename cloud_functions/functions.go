package main

import (
	"bytes"
	"context"
	"fmt"
	"html/template"
	"io"
	"net/http"
	"strings"

	"cloud.google.com/go/storage"
	"github.com/GoogleCloudPlatform/functions-framework-go/functions"
	"google.golang.org/api/iterator"
)

func init() {
	functions.HTTP("dynamic", dynamicHandler)
}

func dynamicHandler(w http.ResponseWriter, r *http.Request) {

	function := r.URL.Query().Get("func")

	// Extract the filename from the path
	switch function {
	case "upload":
		uploadHandler(w, r)
		return
	case "download":
		downloadHandler(w, r)
		return
	default:
		w.WriteHeader(http.StatusNotFound)
		fmt.Fprint(w, "incorrect func, you use correct format for the url /dynamic?func=upload or /dynamic?func=download or /dynamic?func=download&filename=xyz")
	}

	// Use the filename variable as needed

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

func downloadHandler(w http.ResponseWriter, r *http.Request) {
	// Get the filename from the request query parameters
	filename := r.URL.Query().Get("filename")
	if filename == "" {
		listFilesHandler(w, r)
		return
	}

	// Set the Content-Disposition header to trigger a download on the client's browser
	w.Header().Set("Content-Disposition", fmt.Sprintf("attachment; filename=\"%s\"", filename))

	// Set up your Google Cloud Storage client
	ctx := context.Background()
	client, err := storage.NewClient(ctx)
	if err != nil {
		return
	}
	defer client.Close()

	// Create a new bucket handle
	bucket := client.Bucket("ankur_docs")

	// Create a new object handle
	obj := bucket.Object(filename)

	// Create a reader to download the file content
	reader, err := obj.NewReader(ctx)
	if err != nil {
		http.Error(w, "Failed to create reader", http.StatusInternalServerError)
		return
	}
	defer reader.Close()

	// Copy the file content to the response writer
	_, err = io.Copy(w, reader)
	if err != nil {
		http.Error(w, "Failed to copy file content", http.StatusInternalServerError)
		return
	}
}

type GCSFile struct {
	Name     string
	FileSize string
	Metadata string
}

func listFiles(search string) []GCSFile {
	// Set up your Google Cloud Storage client
	ctx := context.Background()
	client, err := storage.NewClient(ctx)
	if err != nil {
		return nil
	}
	defer client.Close()

	// Create a new bucket handle
	bucket := client.Bucket("ankur_docs")

	// List all objects in the bucket
	it := bucket.Objects(ctx, nil)

	var files []GCSFile
	for {
		objAttrs, err := it.Next()
		if err == iterator.Done {
			break
		}
		if err != nil {
			return nil
		}

		if search == "" || strings.Contains(strings.ToLower(objAttrs.Name), strings.ToLower(search)) || strings.Contains(strings.ToLower(objAttrs.Metadata["desc"]), strings.ToLower(search)) {
			files = append(files, GCSFile{
				Name:     objAttrs.Name,
				FileSize: fmt.Sprintf("%d bytes", objAttrs.Size),
				Metadata: objAttrs.Metadata["desc"],
			})
		}
	}

	return files
}

func listFilesHandler(w http.ResponseWriter, r *http.Request) {

	searchTerm := r.URL.Query().Get("search")
	// Set up your Google Cloud Storage client
	files := listFiles(searchTerm)
	// Create a template for the HTML content
	htmlTemplate := `<html><body><ul>{{range .}}<li><a href="/dynamic?func=download&filename={{.Name}}">{{.Name}}</a> ({{.FileSize}})   ({{.Metadata}})  </li>{{end}}</ul></body></html>`
	// Create a new buffer to store the rendered HTML
	var buf bytes.Buffer
	// Execute the template with the files as the data
	tmpl := template.Must(template.New("html").Parse(htmlTemplate))
	err := tmpl.Execute(&buf, files)
	if err != nil {
		http.Error(w, "Failed to render HTML", http.StatusInternalServerError)
		return
	}
	// Write the rendered HTML to the response writer
	fmt.Fprint(w, buf.String())
}
