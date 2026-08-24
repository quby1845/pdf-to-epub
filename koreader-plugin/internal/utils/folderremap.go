package utils

import (
	"path/filepath"
	"strings"
)

// FolderRemapper handles renaming of root folders to avoid collisions.
// When receiving folder transfers, existing folders with the same name
// are remapped to unique names (e.g., "Photos" -> "Photos (1)").
type FolderRemapper struct {
	remap   map[string]string
	saveDir string
}

// NewFolderRemapper creates a FolderRemapper for the given save directory.
// filenames should be sanitized relative paths from the transfer metadata.
// Errors finding unique names are returned; individual file errors are skipped.
func NewFolderRemapper(saveDir string, filenames []string) (*FolderRemapper, error) {
	r := &FolderRemapper{
		remap:   make(map[string]string),
		saveDir: saveDir,
	}

	// Extract all unique root folders from filenames
	rootFolders := make(map[string]bool)
	for _, filename := range filenames {
		sanitizedPath, err := SanitizeRelativePath(filename)
		if err != nil {
			continue
		}
		// Get the first path component (root folder)
		parts := strings.SplitN(filepath.ToSlash(sanitizedPath), "/", 2)
		if len(parts) > 1 {
			// Has subdirectory structure - track root folder
			rootFolders[parts[0]] = true
		}
	}

	// For each root folder, find a unique name if needed
	for root := range rootFolders {
		uniqueRoot, err := FindUniqueFolderName(saveDir, root)
		if err != nil {
			return nil, err
		}
		if uniqueRoot != root {
			r.remap[root] = uniqueRoot
		}
	}

	return r, nil
}

// Apply applies the folder remap to a sanitized path.
// If the path's root folder has been remapped, returns the remapped path.
func (r *FolderRemapper) Apply(sanitizedPath string) string {
	if len(r.remap) == 0 {
		return sanitizedPath
	}

	parts := strings.SplitN(filepath.ToSlash(sanitizedPath), "/", 2)
	if len(parts) > 1 {
		if newRoot, ok := r.remap[parts[0]]; ok {
			return newRoot + "/" + parts[1]
		}
	}
	return sanitizedPath
}

// HasRemap returns true if any folders were remapped.
func (r *FolderRemapper) HasRemap() bool {
	return len(r.remap) > 0
}

// GetRemap returns the remap map (for logging/debugging).
func (r *FolderRemapper) GetRemap() map[string]string {
	// Return a copy to prevent external modification
	result := make(map[string]string, len(r.remap))
	for k, v := range r.remap {
		result[k] = v
	}
	return result
}
