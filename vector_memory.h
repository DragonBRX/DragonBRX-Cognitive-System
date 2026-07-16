#ifndef VECTOR_MEMORY_H
#define VECTOR_MEMORY_H

#include <stddef.h>

// Estrutura para representar um vetor (embedding)
typedef struct {
    float* data;
    size_t dim;
} Vector;

// Estrutura para armazenar uma entrada de memória
typedef struct {
    char* id;
    Vector embedding;
    char* content; // Conteúdo textual associado
} MemoryEntry;

// Inicializa o sistema de memória vetorial
void vm_init(size_t max_entries, size_t embedding_dim);

// Adiciona uma entrada de memória
// Retorna 0 em sucesso, -1 em falha
int vm_add_entry(const char* id, const float* embedding_data, size_t embedding_dim, const char* content);

// Busca as N entradas mais similares a um vetor de consulta
// Retorna um array de MemoryEntry* (os N resultados) e preenche num_results
// O chamador é responsável por liberar a memória retornada
MemoryEntry** vm_search(const float* query_embedding_data, size_t query_dim, int n_results, int* num_results);

// Libera a memória de uma entrada de memória
void vm_free_entry(MemoryEntry* entry);

// Libera a memória do array de resultados de busca
void vm_free_search_results(MemoryEntry** results);

// Libera todos os recursos da memória vetorial
void vm_cleanup();

#endif // VECTOR_MEMORY_H
