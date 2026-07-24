#include "vector_memory.h"
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include <math.h>
#include <jansson.h>

#define MAX_MEMORY_ENTRIES 1000 // Limite para o número de entradas de memória

static MemoryEntry* g_memory_entries = NULL;
static size_t g_current_entries = 0;
static size_t g_max_entries = 0;
static size_t g_embedding_dim = 0;

// Função auxiliar para calcular a similaridade de cosseno
static float cosine_similarity(const float* vec1, const float* vec2, size_t dim) {
    float dot_product = 0.0;
    float norm_vec1 = 0.0;
    float norm_vec2 = 0.0;

    for (size_t i = 0; i < dim; ++i) {
        dot_product += vec1[i] * vec2[i];
        norm_vec1 += vec1[i] * vec1[i];
        norm_vec2 += vec2[i] * vec2[i];
    }

    if (norm_vec1 == 0.0 || norm_vec2 == 0.0) {
        return 0.0; // Evitar divisão por zero
    }

    return dot_product / (sqrt(norm_vec1) * sqrt(norm_vec2));
}

void vm_init(size_t max_entries, size_t embedding_dim) {
    if (g_memory_entries != NULL) {
        vm_cleanup(); // Limpa se já estiver inicializado
    }

    g_max_entries = max_entries;
    g_embedding_dim = embedding_dim;
    g_current_entries = 0;

    g_memory_entries = (MemoryEntry*)malloc(g_max_entries * sizeof(MemoryEntry));
    if (g_memory_entries == NULL) {
        json_t *response = json_object();
        json_object_set_new(response, "status", json_string("error"));
        json_object_set_new(response, "message", json_string("Falha ao alocar memória para entradas de memória."));
        fprintf(stdout, "%s\n", json_dumps(response, 0));
        json_decref(response);
        return;
    }
    json_t *response = json_object();
    json_object_set_new(response, "status", json_string("success"));
    json_object_set_new(response, "message", json_string("Memória vetorial inicializada."));
    json_object_set_new(response, "max_entries", json_integer(g_max_entries));
    json_object_set_new(response, "embedding_dim", json_integer(g_embedding_dim));
    fprintf(stdout, "%s\n", json_dumps(response, 0));
    json_decref(response);
}

int vm_add_entry(const char* id, const float* embedding_data, size_t embedding_dim, const char* content) {
    if (g_memory_entries == NULL || g_current_entries >= g_max_entries || embedding_dim != g_embedding_dim) {
        json_t *response = json_object();
        json_object_set_new(response, "status", json_string("error"));
        json_object_set_new(response, "message", json_string("Memória não inicializada, cheia ou dimensão de embedding incorreta."));
        fprintf(stdout, "%s\n", json_dumps(response, 0));
        json_decref(response);
        return -1;
    }

    MemoryEntry* new_entry = &g_memory_entries[g_current_entries];

    new_entry->id = strdup(id);
    if (new_entry->id == NULL) {
        json_t *response = json_object();
        json_object_set_new(response, "status", json_string("error"));
        json_object_set_new(response, "message", json_string("Falha ao alocar memória para ID."));
        fprintf(stdout, "%s\n", json_dumps(response, 0));
        json_decref(response);
        return -1;
    }

    new_entry->embedding.data = (float*)malloc(embedding_dim * sizeof(float));
    if (new_entry->embedding.data == NULL) {
        free(new_entry->id);
        json_t *response = json_object();
        json_object_set_new(response, "status", json_string("error"));
        json_object_set_new(response, "message", json_string("Falha ao alocar memória para embedding."));
        fprintf(stdout, "%s\n", json_dumps(response, 0));
        json_decref(response);
        return -1;
    }
    memcpy(new_entry->embedding.data, embedding_data, embedding_dim * sizeof(float));
    new_entry->embedding.dim = embedding_dim;

    new_entry->content = strdup(content);
    if (new_entry->content == NULL) {
        free(new_entry->id);
        free(new_entry->embedding.data);
        json_t *response = json_object();
        json_object_set_new(response, "status", json_string("error"));
        json_object_set_new(response, "message", json_string("Falha ao alocar memória para conteúdo."));
        fprintf(stdout, "%s\n", json_dumps(response, 0));
        json_decref(response);
        return -1;
    }

    g_current_entries++;
    json_t *response = json_object();
    json_object_set_new(response, "status", json_string("success"));
    json_object_set_new(response, "message", json_string("Entrada de memória adicionada."));
    json_object_set_new(response, "id", json_string(id));
    json_object_set_new(response, "total_entries", json_integer(g_current_entries));
    fprintf(stdout, "%s\n", json_dumps(response, 0));
    json_decref(response);
    return 0;
}

MemoryEntry** vm_search(const float* query_embedding_data, size_t query_dim, int n_results, int* num_results) {
    if (g_memory_entries == NULL || query_dim != g_embedding_dim) {
        json_t *response = json_object();
        json_object_set_new(response, "status", json_string("error"));
        json_object_set_new(response, "message", json_string("Memória não inicializada ou dimensão de query incorreta."));
        fprintf(stdout, "%s\n", json_dumps(response, 0));
        json_decref(response);
        *num_results = 0;
        return NULL;
    }

    typedef struct {
        MemoryEntry* entry;
        float similarity;
    } SearchResult;

    SearchResult* temp_results = (SearchResult*)malloc(g_current_entries * sizeof(SearchResult));
    if (temp_results == NULL) {
        json_t *response = json_object();
        json_object_set_new(response, "status", json_string("error"));
        json_object_set_new(response, "message", json_string("Falha ao alocar memória para resultados temporários."));
        fprintf(stdout, "%s\n", json_dumps(response, 0));
        json_decref(response);
        *num_results = 0;
        return NULL;
    }

    for (size_t i = 0; i < g_current_entries; ++i) {
        temp_results[i].entry = &g_memory_entries[i];
        temp_results[i].similarity = cosine_similarity(query_embedding_data, g_memory_entries[i].embedding.data, g_embedding_dim);
    }

    // Ordenar os resultados por similaridade (do maior para o menor)
    for (size_t i = 0; i < g_current_entries; ++i) {
        for (size_t j = i + 1; j < g_current_entries; ++j) {
            if (temp_results[i].similarity < temp_results[j].similarity) {
                SearchResult temp = temp_results[i];
                temp_results[i] = temp_results[j];
                temp_results[j] = temp;
            }
        }
    }

    *num_results = (g_current_entries < n_results) ? g_current_entries : n_results;
    MemoryEntry** final_results = (MemoryEntry**)malloc(*num_results * sizeof(MemoryEntry*));
    if (final_results == NULL) {
        json_t *response = json_object();
        json_object_set_new(response, "status", json_string("error"));
        json_object_set_new(response, "message", json_string("Falha ao alocar memória para resultados finais."));
        fprintf(stdout, "%s\n", json_dumps(response, 0));
        json_decref(response);
        free(temp_results);
        *num_results = 0;
        return NULL;
    }

    for (int i = 0; i < *num_results; ++i) {
        final_results[i] = temp_results[i].entry;
    }

    free(temp_results);
    return final_results;
}

void vm_free_entry(MemoryEntry* entry) {
    if (entry) {
        free(entry->id);
        free(entry->embedding.data);
        free(entry->content);
    }
}

void vm_free_search_results(MemoryEntry** results) {
    // Note: As entradas retornadas por vm_search apontam para a memória global g_memory_entries.
    // Apenas o array de ponteiros precisa ser liberado, não as entradas em si.
    free(results);
}

void vm_cleanup() {
    if (g_memory_entries != NULL) {
        for (size_t i = 0; i < g_current_entries; ++i) {
            vm_free_entry(&g_memory_entries[i]);
        }
        free(g_memory_entries);
        g_memory_entries = NULL;
    }
    g_current_entries = 0;
    g_max_entries = 0;
    g_embedding_dim = 0;
    json_t *response = json_object();
    json_object_set_new(response, "status", json_string("success"));
    json_object_set_new(response, "message", json_string("Memória vetorial limpa."));
    fprintf(stdout, "%s\n", json_dumps(response, 0));
    json_decref(response);
}

int main(int argc, char *argv[]) {
    char buffer[4096];
    while (fgets(buffer, sizeof(buffer), stdin) != NULL) {
        json_error_t error;
        json_t *root = json_loads(buffer, 0, &error);

        if (!root) {
            json_t *response = json_object();
            json_object_set_new(response, "status", json_string("error"));
            json_object_set_new(response, "message", json_string(error.text));
            fprintf(stdout, "%s\n", json_dumps(response, 0));
            json_decref(response);
            fflush(stdout);
            continue;
        }

        json_t *command_json = json_object_get(root, "command");
        if (!json_is_string(command_json)) {
            json_t *response = json_object();
            json_object_set_new(response, "status", json_string("error"));
            json_object_set_new(response, "message", json_string("Comando JSON inválido."));
            fprintf(stdout, "%s\n", json_dumps(response, 0));
            json_decref(response);
            json_decref(root);
            fflush(stdout);
            continue;
        }
        const char *command = json_string_value(command_json);

        if (strcmp(command, "init") == 0) {
            json_t *max_entries_json = json_object_get(root, "max_entries");
            json_t *embedding_dim_json = json_object_get(root, "embedding_dim");
            size_t max_entries = json_is_integer(max_entries_json) ? json_integer_value(max_entries_json) : 100;
            size_t embedding_dim = json_is_integer(embedding_dim_json) ? json_integer_value(embedding_dim_json) : 384;
            vm_init(max_entries, embedding_dim);
        } else if (strcmp(command, "add") == 0) {
            json_t *id_json = json_object_get(root, "id");
            json_t *content_json = json_object_get(root, "content");
            json_t *embedding_json = json_object_get(root, "embedding");

            if (!json_is_string(id_json) || !json_is_string(content_json) || !json_is_array(embedding_json)) {
                json_t *response = json_object();
                json_object_set_new(response, "status", json_string("error"));
                json_object_set_new(response, "message", json_string("Dados de entrada inválidos para o comando add."));
                fprintf(stdout, "%s\n", json_dumps(response, 0));
                json_decref(response);
                json_decref(root);
                fflush(stdout);
                continue;
            }

            const char *id = json_string_value(id_json);
            const char *content = json_string_value(content_json);
            size_t embedding_dim_received = json_array_size(embedding_json);
            float *embedding_data = (float*)malloc(embedding_dim_received * sizeof(float));
            if (!embedding_data) {
                json_t *response = json_object();
                json_object_set_new(response, "status", json_string("error"));
                json_object_set_new(response, "message", json_string("Falha ao alocar memória para embedding data."));
                fprintf(stdout, "%s\n", json_dumps(response, 0));
                json_decref(response);
                json_decref(root);
                fflush(stdout);
                continue;
            }

            for (size_t i = 0; i < embedding_dim_received; ++i) {
                json_t *value = json_array_get(embedding_json, i);
                if (!json_is_number(value)) {
                    free(embedding_data);
                    json_t *response = json_object();
                    json_object_set_new(response, "status", json_string("error"));
                    json_object_set_new(response, "message", json_string("Embedding contém valores não numéricos."));
                    fprintf(stdout, "%s\n", json_dumps(response, 0));
                    json_decref(response);
                    json_decref(root);
                    fflush(stdout);
                    continue;
                }
                embedding_data[i] = (float)json_number_value(value);
            }
            vm_add_entry(id, embedding_data, embedding_dim_received, content);
            free(embedding_data);
        } else if (strcmp(command, "search") == 0) {
            json_t *query_embedding_json = json_object_get(root, "query_embedding");
            json_t *n_results_json = json_object_get(root, "n_results");

            if (!json_is_array(query_embedding_json)) {
                json_t *response = json_object();
                json_object_set_new(response, "status", json_string("error"));
                json_object_set_new(response, "message", json_string("Query embedding inválido."));
                fprintf(stdout, "%s\n", json_dumps(response, 0));
                json_decref(response);
                json_decref(root);
                fflush(stdout);
                continue;
            }

            size_t query_dim = json_array_size(query_embedding_json);
            float *query_embedding_data = (float*)malloc(query_dim * sizeof(float));
            if (!query_embedding_data) {
                json_t *response = json_object();
                json_object_set_new(response, "status", json_string("error"));
                json_object_set_new(response, "message", json_string("Falha ao alocar memória para query embedding data."));
                fprintf(stdout, "%s\n", json_dumps(response, 0));
                json_decref(response);
                json_decref(root);
                fflush(stdout);
                continue;
            }

            for (size_t i = 0; i < query_dim; ++i) {
                json_t *value = json_array_get(query_embedding_json, i);
                if (!json_is_number(value)) {
                    free(query_embedding_data);
                    json_t *response = json_object();
                    json_object_set_new(response, "status", json_string("error"));
                    json_object_set_new(response, "message", json_string("Query embedding contém valores não numéricos."));
                    fprintf(stdout, "%s\n", json_dumps(response, 0));
                    json_decref(response);
                    json_decref(root);
                    fflush(stdout);
                    continue;
                }
                query_embedding_data[i] = (float)json_number_value(value);
            }

            int n_results = json_is_integer(n_results_json) ? json_integer_value(n_results_json) : 3;
            int num_found_results;
            MemoryEntry** results = vm_search(query_embedding_data, query_dim, n_results, &num_found_results);
            
            json_t *response = json_object();
            json_object_set_new(response, "status", json_string("success"));
            json_t *results_array = json_array();
            for (int i = 0; i < num_found_results; ++i) {
                json_t *result_obj = json_object();
                json_object_set_new(result_obj, "id", json_string(results[i]->id));
                json_object_set_new(result_obj, "content", json_string(results[i]->content));
                json_array_append_new(results_array, result_obj);
            }
            json_object_set_new(response, "results", results_array);
            fprintf(stdout, "%s\n", json_dumps(response, 0));
            json_decref(response);
            vm_free_search_results(results);
            free(query_embedding_data);
        } else if (strcmp(command, "cleanup") == 0) {
            vm_cleanup();
        } else {
            json_t *response = json_object();
            json_object_set_new(response, "status", json_string("error"));
            json_object_set_new(response, "message", json_string("Comando desconhecido ou formato inválido."));
            fprintf(stdout, "%s\n", json_dumps(response, 0));
            json_decref(response);
        }
        json_decref(root);
        fflush(stdout);
    }
    return 0;
}
