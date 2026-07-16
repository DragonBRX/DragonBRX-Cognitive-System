#ifndef SYNAPTIC_STORAGE_H
#define SYNAPTIC_STORAGE_H

#include <stddef.h>
#include <time.h>

// Estrutura para representar um vetor (embedding)
typedef struct {
    float* data;
    size_t dim;
} Vector;

// Estrutura para armazenar uma entrada de memória (sinapse)
typedef struct {
    char* id;
    Vector embedding;
    char* content; // Conteúdo textual associado
    time_t last_accessed; // Timestamp do último acesso para plasticidade
    float strength;       // Força sináptica (importância/frequência de acesso)
} SynapticEntry;

// Inicializa o Módulo de Armazenamento Sináptico
void ss_init(size_t max_entries, size_t embedding_dim);

// Adiciona uma entrada sináptica
// Retorna 0 em sucesso, -1 em falha
int ss_add_entry(const char* id, const float* embedding_data, size_t embedding_dim, const char* content);

// Busca as N entradas sinápticas mais similares a um vetor de consulta
// Retorna um array de SynapticEntry* (os N resultados) e preenche num_results
// O chamador é responsável por liberar a memória do array de ponteiros, não das entradas em si.
SynapticEntry** ss_search(const float* query_embedding_data, size_t query_dim, int n_results, int* num_results);

// Atualiza a força sináptica e o timestamp de acesso de uma entrada
void ss_update_plasticity(const char* id);

// Aplica o decaimento (esquecimento) a todas as entradas de memória
void ss_apply_decay(float decay_rate, time_t current_time);

// Libera a memória de uma entrada sináptica
void ss_free_entry(SynapticEntry* entry);

// Libera a memória do array de resultados de busca
void ss_free_search_results(SynapticEntry** results);

// Libera todos os recursos do Módulo de Armazenamento Sináptico
void ss_cleanup();

#endif // SYNAPTIC_STORAGE_H
